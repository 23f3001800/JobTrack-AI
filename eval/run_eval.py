"""Eval CLI — run evaluations on past applications or workspace files.

Usage:
    # Evaluate all applications from the tracker
    python -m eval.run_eval

    # Evaluate specific workspace files
    python -m eval.run_eval --workspace ./workspace

    # Save results to file
    python -m eval.run_eval --output docs/evaluation/eval_results.json

WHY a CLI instead of just a function?
1. CI/CD can run this as a step: `python -m eval.run_eval --output results.json`
2. Developers can run locally to check quality before committing
3. Results are saved as JSON for the README metrics
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _load_workspace_apps(workspace_dir: str) -> list[dict]:
    """Load application data from workspace files.

    WHY scan workspace instead of reading from DB?
    The workspace is the source of truth for generated content.
    Even without Supabase, we can evaluate output quality by
    reading the files the agent wrote.

    Expected workspace structure:
    workspace/
    ├── CompanyA_cover_letter.md
    ├── CompanyA_cv_bullets.md
    ├── CompanyA_job_analysis.md
    └── CompanyA_company_profile.md
    """
    workspace = Path(workspace_dir)
    if not workspace.exists():
        print(f"Workspace not found: {workspace_dir}")
        return []

    # Group files by company prefix
    companies: dict[str, dict] = {}
    for f in workspace.iterdir():
        if not f.is_file() or not f.suffix == ".md":
            continue

        name = f.stem
        # Try to extract company name from filename pattern
        for suffix in ["_cover_letter", "_cv_bullets", "_job_analysis",
                       "_company_profile", "_outreach_dm"]:
            if name.endswith(suffix):
                company = name.replace(suffix, "").replace("_", " ").title()
                if company not in companies:
                    companies[company] = {"company": company}

                field_map = {
                    "_cover_letter": "cover_letter",
                    "_cv_bullets": "tailored_bullets",
                    "_job_analysis": "job_analysis",
                    "_company_profile": "company_profile",
                }
                field = field_map.get(suffix)
                if field:
                    companies[company][field] = f.read_text()
                break

    return list(companies.values())


def _load_tracker_apps() -> list[dict]:
    """Load applications from the database/tracker."""
    try:
        from db import get_db
        db = get_db()
        return db.get_applications()
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate JobTrack AI application quality"
    )
    parser.add_argument(
        "--workspace", "-w",
        default=os.getenv("WORKSPACE_DIR", "./workspace"),
        help="Path to workspace directory with generated files",
    )
    parser.add_argument(
        "--output", "-o",
        default="docs/evaluation/eval_results.json",
        help="Output file for eval results",
    )
    parser.add_argument(
        "--source",
        choices=["workspace", "tracker", "both"],
        default="both",
        help="Where to load applications from",
    )
    args = parser.parse_args()

    # Load applications
    apps = []
    if args.source in ("workspace", "both"):
        ws_apps = _load_workspace_apps(args.workspace)
        apps.extend(ws_apps)
        print(f"📂 Loaded {len(ws_apps)} applications from workspace")

    if args.source in ("tracker", "both"):
        tr_apps = _load_tracker_apps()
        apps.extend(tr_apps)
        print(f"📊 Loaded {len(tr_apps)} applications from tracker")

    if not apps:
        print("❌ No applications found to evaluate")
        sys.exit(1)

    # Filter to apps that have enough content to evaluate
    evaluatable = [
        a for a in apps
        if a.get("cover_letter") or a.get("tailored_bullets")
    ]

    if not evaluatable:
        print("❌ No applications with cover letters or bullets to evaluate")
        sys.exit(1)

    print(f"\n🔍 Evaluating {len(evaluatable)} applications...\n")

    # Run evaluation
    from eval.evaluator import evaluate_batch
    results = evaluate_batch(evaluatable)

    # Print results
    print("=" * 60)
    print("📊 EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Average Score:      {results['avg_score']} / 5")
    print(f"  Pass Rate (≥4):     {results['pass_rate']}")
    print(f"  Personalisation:    {results['personalisation_rate']}")
    print(f"  Role Match:         {results['role_match_rate']}")
    print(f"  Professional Tone:  {results['professional_tone_rate']}")
    print()

    for r in results["results"]:
        emoji = "✅" if r["overall"] >= 4 else "⚠️" if r["overall"] >= 3 else "❌"
        print(f"  {emoji} {r['company']}: {r['overall']}/5 — {r['reasoning'][:80]}...")

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {args.output}")


if __name__ == "__main__":
    main()
