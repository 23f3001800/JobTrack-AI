import os, json, uuid
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from agent.graph import app as agent_app, JobState
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="JobTrack AI", version="1.0.0")
app.state.limiter = limiter
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


security = HTTPBearer()

def verify_key(creds: HTTPAuthorizationCredentials = Depends(security)):
    if creds.credentials != os.getenv("API_KEY", "dev-key"):
        raise HTTPException(401, "Invalid API key")
    return creds.credentials


class RunRequest(BaseModel):
    job_url:         str = Field(..., description="URL of the job posting")
    user_background: str = Field("Python developer", max_length=1000)

# Field names → human-readable step labels for the client UI
STEP_LABELS = {
    "job_analysis":     "Job analysis",
    "company_profile":  "Company research",
    "tailored_bullets": "CV tailoring",
    "cover_letter":     "Cover letter",
    "outreach_dm":      "LinkedIn DM",
    "log_result":       "Application logged",
}

@app.post("/run", tags=["agent"])
@limiter.limit("5/minute")   # Each run costs $0.10–0.50 in API calls
async def run_agent(request: Request, body: RunRequest,
                    _=Depends(verify_key)):
    thread_id = body.job_url.split("/")[-1] + "-" + str(uuid.uuid4())[:4]
    initial = JobState(
        job_url=body.job_url, user_background=body.user_background,
        job_analysis="", company_profile="", tailored_bullets="",
        cover_letter="", outreach_dm="", log_result="",
        messages=[], iterations=0
    )
    config = {"configurable": {"thread_id": thread_id}}
    async def stream_steps():
        prev_state = {}
        try:
            # WHY stream_mode="values"?
            # Yields the full state after every node execution.
            # We compare current vs previous state to detect
            # which field was just populated — that's the
            # completed step we report to the client.
            async for state in agent_app.astream(
                initial, config=config, stream_mode="values"
            ):
                for field, label in STEP_LABELS.items():
                    if state.get(field) and not prev_state.get(field):
                        chunk = {
                            "step": label,
                            "status": "done",
                            "preview": state[field][:120].replace("\n"," ")
                        }
                        yield json.dumps(chunk) + "\n"
                prev_state = dict(state)
            # Final summary line
            yield json.dumps({
                "step": "complete", "status": "done",
                "thread_id": thread_id,
                "files": "Check workspace/ directory"
            }) + "\n"

        except Exception as e:
            yield json.dumps({"step": "error", "message": str(e)}) + "\n"

    return StreamingResponse(stream_steps(),
                             media_type="application/x-ndjson")


@app.get("/tracker", tags=["tracker"])
async def get_tracker(_=Depends(verify_key)):
    """Return all tracked job applications from tracker.json."""
    tracker = Path(os.getenv("WORKSPACE_DIR","./workspace")) / "tracker.json"
    if not tracker.exists():
        return {"applications": [], "total": 0}
    data = json.loads(tracker.read_text())
    return {"applications": data, "total": len(data)}

@app.get("/health")
def health():
    return {"status": "ok", "mcp_tools": 4, "version": "1.0.0"}