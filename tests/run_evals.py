import json
import os
import sys
from pathlib import Path
from anthropic import Anthropic
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

client = Anthropic()


def parse_llm_json(text: str):
    text = text.strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return json.loads(text)

class ApplicationScore(BaseModel):
    overall:           int    # 1-5
    is_personalised:   bool   # mentions company product/culture specifically
    role_matched:      bool   # CV bullets align with stated job requirements
    professional_tone: bool   # reads like a real human engineer wrote it
    reasoning:         str

def judge_application(
    job_analysis: str, company_profile: str,
    cover_letter: str, tailored_bullets: str
) -> ApplicationScore:
    # WHY use Sonnet (not Haiku) for judging?
    # Haiku is great at classification but weak at nuanced judgment.
    # Sonnet catches subtle issues: "this mentions 'ML' but the job
    # requires 'LLM experience' specifically" — Haiku misses this.
    # One Sonnet call per eval ≈ $0.003. Worth it for accuracy.
    resp = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=400,
        messages=[{"role":"user","content":
            f"""You are a senior hiring manager reviewing this job application.
Rate its quality honestly. Mediocre AI-generated applications score 2-3.
Outstanding personalised applications score 5.

Job requirements: {job_analysis[:400]}
Company profile: {company_profile[:300]}
Cover letter: {cover_letter[:600]}
CV bullets: {tailored_bullets[:400]}

Respond ONLY with valid JSON — no preamble:
{{"overall":1-5,"is_personalised":bool,"role_matched":bool,"professional_tone":bool,"reasoning":"max 2 sentences"}}"""}]
    )
    return ApplicationScore(**parse_llm_json(resp.content[0].text))

def eval_workspace(pass_threshold: float = 3.5):
    workspace = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    tracker   = workspace / "tracker.json"

    if not tracker.exists():
        print("No applications found. Run the agent on real job URLs first.")
        sys.exit(0)
    applications = json.loads(tracker.read_text())
    if not applications:
        print("Tracker is empty.")
        sys.exit(0)

    all_scores, results = [], []
    for app in applications:
        company = app["company"]
        slug    = company.lower().replace(" ","_")

        cl_path = workspace / f"{slug}_cover_letter.txt"
        if not cl_path.exists():
            print(f"  ⚠ No cover letter found for {company} — skipping")
            continue

        cover_letter = cl_path.read_text()
        # Read research from state if persisted, else use tracker data
        job_analysis    = app.get("job_analysis",    f"Role at {company}")
        company_profile = app.get("company_profile", f"{company} profile")
        tailored_bullets = app.get("tailored_bullets", "")

        print(f"Evaluating: {company}...")
        score = judge_application(
            job_analysis, company_profile, cover_letter, tailored_bullets
        )
        all_scores.append(score.overall)
        results.append({
            "company":           company,
            "overall":           score.overall,
            "is_personalised":   score.is_personalised,
            "role_matched":      score.role_matched,
            "professional_tone": score.professional_tone,
            "reasoning":         score.reasoning,
        })
        print(f"  Score: {score.overall}/5 — {score.reasoning}")

    avg = sum(all_scores) / len(all_scores)
    personalised_rate = sum(1 for r in results if r["is_personalised"]) / len(results)

    print(f"\n{'='*45}")
    print(f"Avg quality:       {avg:.2f}/5")
    print(f"Personalised:      {personalised_rate:.0%}")
    print(f"Role matched:      {sum(1 for r in results if r['role_matched'])/len(results):.0%}")
    print(f"Professional tone: {sum(1 for r in results if r['professional_tone'])/len(results):.0%}")

    out = Path("docs/evaluation/eval_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"avg_score":avg,"results":results}, indent=2))
    if avg < pass_threshold:
        print(f"\n❌ Eval gate: avg {avg:.2f} < {pass_threshold} — improve prompts")
        sys.exit(1)
    print(f"\n✅ Eval gate passed — {avg:.2f}/5")

if __name__ == "__main__":
    eval_workspace()