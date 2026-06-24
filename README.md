# 🎯 JobTrack AI — Multi-Agent Job Application System

> **I used this agent to prepare my application for this interview.**

**Problem:** A properly tailored application (company research + CV match +
personalised cover letter + LinkedIn DM) takes **2 hours per role**. Most people
either apply generically (low callback rate) or apply to 5 roles carefully
(unsustainable at scale).

**Solution:** A **5-agent LangGraph pipeline** that researches the company,
analyses your fit, tailors your CV, writes a personalised cover letter, generates
a PDF resume, and quality-checks everything — in **under 8 minutes**. A built-in
self-review loop ensures output quality stays above 4/5.

**[Live Dashboard](https://jobtrack.up.railway.app)** ·
**[API Docs](https://jobtrack.up.railway.app/docs)** ·
**[LangSmith Traces](https://smith.langchain.com)**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SUPERVISOR                               │
│  Routes state through agents • Manages quality feedback loop    │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │          │
   ┌───▼───┐ ┌───▼────┐ ┌──▼───┐ ┌───▼────┐ ┌───▼────┐
   │ Scout │ │Research│ │Writer│ │Quality │ │Applier │
   │  🔍   │ │  🏢    │ │  ✍️   │ │  ⭐    │ │  📤    │
   └───┬───┘ └───┬────┘ └──┬───┘ └───┬────┘ └───┬────┘
       │          │          │          │          │
  scrape_job  research    tailor_cv  review    log_app
  search_jobs  company    cover_ltr  score     gen_pdf
              role_fit    outreach
```

### Pipeline Flow

| Step | Agent | Action | Tool |
|------|-------|--------|------|
| 1 | **Scout** 🔍 | Scrape job posting OR search for jobs | Playwright + DuckDuckGo |
| 2 | **Research** 🏢 | Company intel + role fit analysis | Web scraping + Claude |
| 3 | **Writer** ✍️ | Tailor CV + cover letter + LinkedIn DM | Claude Sonnet |
| 4 | **Quality** ⭐ | LLM-as-judge review (loops if score < 4) | Claude Sonnet |
| 5 | **Applier** 📤 | Log to DB + generate tailored PDF resume | Supabase + ReportLab |

### Quality Loop

```
Writer ──→ Quality ──→ Score ≥ 4? ──→ Yes ──→ Applier
                         │
                         No (max 2 retries)
                         │
                         ▼
                    Writer (rewrite with feedback)
```

The Quality agent scores output 1-5 on: personalisation, role match, and professional
tone. If score < 4, it sends detailed feedback back to the Writer for rewriting.
This ensures **consistently high-quality output** without human intervention.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Orchestration** | LangGraph (StateGraph) | Conditional routing, quality loops, state persistence |
| **LLM** | Claude Sonnet 4 + Haiku | Sonnet for quality writing, Haiku for extraction (10x cheaper) |
| **Backend** | FastAPI + Streaming NDJSON | Real-time progress updates to frontend |
| **Frontend** | Next.js 14 + TypeScript | App Router, server components, glass-dark UI |
| **Database** | Supabase PostgreSQL | RLS per-user, profiles + jobs + applications |
| **Auth** | Supabase Auth + JWT | Dual-mode: JWT for dashboard, API key for CLI/MCP |
| **PDF** | ReportLab | ATS-friendly tailored resumes per application |
| **Scraping** | Playwright + BeautifulSoup | JS-rendered pages with fallback to requests |
| **Search** | DuckDuckGo (ddgs) | No API key needed, detects job board source |
| **Observability** | LangSmith | Traces every agent step, tool call, and quality score |
| **CI/CD** | GitHub Actions → Railway | Auto-deploy on push to main |
| **MCP** | Claude Desktop integration | "List my applications" from Claude Desktop |

---

## Eval Scores (LLM-as-Judge)

Scored by Claude Sonnet acting as a hiring manager on 3 real applications:

| Metric | Score |
|--------|-------|
| **Overall quality** | 4.2 / 5 |
| **Personalisation** | 100% |
| **Role match** | 100% |
| **Professional tone** | 100% |

> See [`docs/evaluation/`](docs/evaluation/) for full results and eval framework.

---

## Dashboard

The Next.js dashboard provides:

- **🔍 Job Search** — Discover jobs across LinkedIn, Indeed, Greenhouse, Lever
- **🚀 One-Click Run** — Paste a URL, watch agents work in real-time (streaming)
- **📋 Application Tracker** — Status management, quality scores, expandable details
- **📊 Stats Dashboard** — Applications count, avg quality, interview conversion
- **📄 PDF Downloads** — Per-job tailored resumes with ATS-friendly formatting

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+ (for dashboard)
- `ANTHROPIC_API_KEY` from [console.anthropic.com](https://console.anthropic.com)

### Backend
```bash
git clone https://github.com/you/jobtrack-ai && cd jobtrack-ai
pip install -r requirements.txt && playwright install chromium
cp .env.example .env  # Add ANTHROPIC_API_KEY, set CV_PATH
uvicorn api.main:app --port 8000 --reload
```

### Dashboard
```bash
cd dashboard
npm install
cp .env.example .env.local  # Points to http://localhost:8000
npm run dev  # → http://localhost:3000
```

### MCP (Claude Desktop)
```json
{"mcpServers": {"jobtrack": {"command": "python", "args": ["/path/to/mcp/server.py"]}}}
```
Then ask Claude: *"Search for Python AI engineer jobs"* or *"List my applications"*

### Docker
```bash
docker compose up --build  # Backend on :8000, Dashboard on :3000
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/run` | JWT/Key | Execute multi-agent pipeline (streaming NDJSON) |
| `POST` | `/jobs/search` | JWT/Key | Search for job postings |
| `POST` | `/jobs/save` | JWT/Key | Save a job to pipeline |
| `GET` | `/tracker` | JWT/Key | List applications (user-scoped) |
| `PATCH` | `/tracker/{id}/status` | JWT/Key | Update application status |
| `DELETE` | `/tracker/{id}` | JWT/Key | Delete an application |
| `POST` | `/generate-pdf` | JWT/Key | Generate tailored PDF resume |
| `POST` | `/interview-prep` | JWT/Key | Generate tailored interview questions |
| `POST` | `/followup` | JWT/Key | Generate follow-up messages (email/LinkedIn) |
| `GET` | `/export/csv` | JWT/Key | Export applications as CSV |
| `GET` | `/download/{file}` | JWT/Key | Download generated files |
| `POST` | `/auth/signup` | None | Create account |
| `POST` | `/auth/login` | None | Get JWT tokens |
| `GET` | `/auth/profile` | JWT/Key | Get user profile |
| `PATCH` | `/auth/profile` | JWT | Update profile |
| `GET` | `/admin/stats` | Admin | System statistics |
| `GET` | `/health` | None | Health check |

---

## Project Structure

```
jobtrack-ai/
├── agent/
│   ├── graph.py              # LangGraph StateGraph orchestrator
│   └── agents/               # 6 sub-agent modules
│       ├── supervisor.py     # Routes state through pipeline
│       ├── scout.py          # Scrapes + searches jobs
│       ├── research.py       # Company intel + fit analysis
│       ├── writer.py         # CV, cover letter, DM generation
│       ├── quality.py        # LLM-as-judge scoring + feedback
│       └── applier.py        # Logging + PDF generation
├── api/
│   ├── main.py               # FastAPI app with streaming
│   ├── auth.py               # JWT + API key dual-mode auth
│   ├── routes_auth.py        # Signup, login, profile
│   ├── routes_admin.py       # Admin stats
│   └── routes_jobs.py        # Job search + save
├── tools/
│   ├── scraper.py            # Playwright + BS4 job scraping
│   ├── searcher.py           # DuckDuckGo job discovery
│   ├── researcher.py         # Company research + role fit
│   ├── cv_processor.py       # CV tailoring + cover letters
│   ├── quality.py            # Review + scoring tools
│   ├── pdf_generator.py      # ReportLab PDF resumes
│   ├── schemas.py            # 11 tool schemas (single source of truth)
│   └── executor.py           # Tool dispatcher with LangSmith tracing
├── db/
│   ├── client.py             # Dual-backend: Supabase + JSON fallback
│   └── migrations.sql        # PostgreSQL schema with RLS
├── dashboard/                # Next.js 14 frontend
│   ├── app/                  # App Router pages
│   └── lib/api.ts            # Typed API client with streaming
├── mcp/server.py             # Claude Desktop MCP server
├── tests/test_graph.py       # Pipeline integration tests
├── Dockerfile                # Multi-stage production build
└── docker-compose.yml        # Full stack deployment
```

---

## What I'd Build Next

1. **Browser Automation** — Auto-fill application forms via Playwright
2. **Interview Prep** — Generate likely questions from job + company profile
3. **Follow-up Scheduler** — Draft polite follow-ups if no reply in 7 days
4. **A/B Test Letters** — Track which cover letter style gets more callbacks
5. **Kanban Board** — Drag-and-drop application tracking with swimlanes