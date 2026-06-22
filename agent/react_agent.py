import os
from anthropic import Anthropic
from tools.schemas import ALL_TOOLS
from tools.executor import execute_tool
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are JobTrack AI — an autonomous job application agent.

Given a job URL and a user's background, you MUST call tools in this exact order:
1. scrape_job_url — extract job details
2. research_company — build company profile  
3. tailor_cv_bullets — personalise CV to this role
4. write_cover_letter — write personalised cover letter
5. write_outreach_dm — draft LinkedIn cold DM
6. log_application — save everything to tracker

Always complete ALL 6 steps. Never skip a step.
Be thorough — the quality of each step feeds into the next."""

def run(job_url: str, user_background: str = "") -> dict:
    client = Anthropic()
    messages = [{
        "role": "user",
        "content": f"Process this job application:\nJob URL: {job_url}\nMy background: {user_background}"
    }]

    results = {}
    iteration = 0
    max_iter = int(os.getenv("MAX_AGENT_ITERATIONS", 10))

    print(f"\n{'='*55}")
    print(f"JobTrack AI — processing: {job_url}")
    print(f"{'='*55}")

    while iteration < max_iter:
        iteration += 1
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=ALL_TOOLS,
            messages=messages
        )
    
        # Collect tool calls from this response
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(f"\n→ Tool called: {block.name}")
                print(f"  Args: {list(block.input.keys())}")
                result = execute_tool(block.name, block.input)
                results[block.name] = result
                print(f"  Result: {result[:80]}...")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        # Append assistant response + tool results to history
        messages.append({"role": "assistant", "content": resp.content})
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Done when no more tool calls
        if resp.stop_reason == "end_turn":
            final_text = "".join(
                b.text for b in resp.content if hasattr(b, "text")
            )
            print(f"\n{'='*55}")
            print(f"✓ Done in {iteration} iterations")
            print(f"✓ Tools used: {list(results.keys())}")
            return {"status": "complete", "results": results,
                    "summary": final_text}

    return {"status": "max_iterations_reached", "results": results}

if __name__ == "__main__":
    output = run(
        job_url="https://www.ycombinator.com/companies/great-question/jobs/J5TNvQH-ai-engineer-intern",
        user_background="Python developer, built RAG systems and LangGraph agents, 1 year experience"
    )
    print(f"\nFinal status: {output['status']}")