"""Sub-agent modules for the multi-agent JobTrack AI system.

Architecture overview:
- Supervisor: Deterministic router that decides which agent runs next
- Scout: Job scraping and discovery (uses Haiku for speed)
- Research: Company research + role fit analysis (uses Haiku)
- Writer: Content generation — cover letter, CV bullets, DM (uses Sonnet for quality)
- Quality: Self-review with rewrite feedback loop (uses Sonnet for judgment)
- Applier: Logs application, later: auto-apply via Playwright

The supervisor routes based on state — no LLM needed for routing decisions.
Each sub-agent has its own system prompt and tool subset.
"""
