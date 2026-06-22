import os
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from anthropic import Anthropic
from tools.schemas import ALL_TOOLS
from tools.executor import execute_tool
from langsmith import traceable, get_current_run_tree
from dotenv import load_dotenv
load_dotenv()

if os.getenv("LANGCHAIN_TRACING_V2") == "true":
    os.environ.setdefault("LANGCHAIN_PROJECT", "jobtrack-ai")

class JobState(TypedDict):
    job_url:          str
    user_background:  str
    job_analysis:     str   # populated by step 1
    company_profile:  str   # populated by step 2
    tailored_bullets: str   # populated by step 3
    cover_letter:     str   # populated by step 4
    outreach_dm:      str   # populated by step 5
    log_result:       str   # populated by step 6
    messages: Annotated[list, operator.add]  # full message history
    iterations: int

client = Anthropic()

ORCHESTRATOR_SYSTEM = """You are JobTrack AI — a job application orchestrator.
You have 6 tools. Call them in ORDER, one at a time:
1. scrape_job_url → get job details
2. research_company → build company profile  
3. tailor_cv_bullets → personalise CV
4. write_cover_letter → draft cover letter
5. write_outreach_dm → draft LinkedIn DM
6. log_application → save everything (IMPORTANT: pass ALL outputs from previous steps including job_analysis, company_profile, tailored_bullets, cover_letter, and outreach_dm)

Check which steps are already done in the user message before deciding which tool to call next.
Never call a step that is already marked complete."""

@traceable(name="orchestrator-node", tags=["agent"])
def orchestrator(state: JobState) -> dict:
    """LLM decides which tool to call next based on what's done."""
    # Build status message so LLM knows what's done
    # WHY pass status explicitly? Without it, the LLM might
    # re-run completed steps (wasting money and time).
    status = f"""
Job URL: {state['job_url']}
Background: {state['user_background']}

Steps completed:
- Step 1 (scrape): {'DONE' if state.get('job_analysis') else 'PENDING'}
- Step 2 (research): {'DONE' if state.get('company_profile') else 'PENDING'}
- Step 3 (tailor CV): {'DONE' if state.get('tailored_bullets') else 'PENDING'}
- Step 4 (cover letter): {'DONE' if state.get('cover_letter') else 'PENDING'}
- Step 5 (DM): {'DONE' if state.get('outreach_dm') else 'PENDING'}
- Step 6 (log): {'DONE' if state.get('log_result') else 'PENDING'}

Call the next PENDING step now."""

    messages = state.get("messages", [])
    messages = messages + [{"role": "user", "content": status}]

    run = get_current_run_tree()
    resp = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=1024,
        system=ORCHESTRATOR_SYSTEM,
        tools=ALL_TOOLS, messages=messages
    )

    if run:
        run.add_metadata({
            "input_tokens":  resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "cost_usd": resp.usage.input_tokens * 0.000003
                        + resp.usage.output_tokens * 0.000015,
            "iteration": state.get("iterations", 0)
        })

    return {"messages": [{"role": "assistant", "content": resp.content}],
            "iterations": state.get("iterations", 0) + 1}


def tool_executor(state: JobState) -> dict:
    """Execute all tool_use blocks from the last assistant message."""
    last = state["messages"][-1]
    tool_results = []
    updates = {}

    for block in last["content"]:
        if not hasattr(block, "type") or block.type != "tool_use":
            continue
        print(f"  → Executing: {block.name}")
        result = execute_tool(block.name, block.input)

        # This is how upstream nodes (the LLM) know what's done.
        # When the orchestrator sees state['job_analysis'] is set,
        # it knows to skip step 1 and call step 2 instead.
        field_map = {
            "scrape_job_url":     "job_analysis",
            "research_company":   "company_profile",
            "tailor_cv_bullets":  "tailored_bullets",
            "write_cover_letter": "cover_letter",
            "write_outreach_dm":  "outreach_dm",
            "log_application":    "log_result",
        }
        if block.name in field_map:
            updates[field_map[block.name]] = result

        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result
        })
    return {**updates,
            "messages": [{"role": "user", "content": tool_results}]}

def should_continue(state: JobState) -> str:
    # All 6 steps done?
    all_done = all([
        state.get("job_analysis"), state.get("company_profile"),
        state.get("tailored_bullets"), state.get("cover_letter"),
        state.get("outreach_dm"), state.get("log_result")
    ])
    if all_done or state.get("iterations", 0) >= 10:
        return "end"
    last = state["messages"][-1]
    has_tools = any(
        hasattr(b, "type") and b.type == "tool_use"
        for b in last.get("content", [])
    )
    return "tools" if has_tools else "end"

# Build the graph
builder = StateGraph(JobState)
builder.add_node("orchestrator", orchestrator)
builder.add_node("tools", tool_executor)
builder.set_entry_point("orchestrator")
builder.add_conditional_edges("orchestrator", should_continue,
                               {"tools": "tools", "end": END})
builder.add_edge("tools", "orchestrator")


# you can resume from step 4 using the same thread_id.
# In production this would be a PostgresSaver instead.
checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)

def run(job_url: str, user_background: str) -> dict:
    thread_id = job_url.split("/")[-1]  # unique per job URL
    initial = JobState(
        job_url=job_url, user_background=user_background,
        job_analysis="", company_profile="", tailored_bullets="",
        cover_letter="", outreach_dm="", log_result="",
        messages=[], iterations=0
    )
    config = {"configurable": {"thread_id": thread_id}}
    final = app.invoke(initial, config=config)
    return {"status": "complete",
            "cover_letter": final.get("cover_letter"),
            "outreach_dm": final.get("outreach_dm"),
            "tailored_bullets": final.get("tailored_bullets")}