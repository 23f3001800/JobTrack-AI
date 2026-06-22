# JobTrack-AI
autonomous 6-step job application workflow agent — for job seekers


curl -X POST http://localhost:8001/run -H "Authorization: Bearer dev-secret-key" -d '{"job_url":"https://www.ycombinator.com/companies/14-ai/jobs/KoEfdhc-full-stack-engineering-internship-now-and-summer-2026"}'


curl -X POST http://localhost:8000/run \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"job_url":"https://www.ycombinator.com/companies/14-ai/jobs/KoEfdhc-full-stack-engineering-internship-now-and-summer-2026"}'

  =============================================
Avg quality:       2.20/5
Personalised:      20%
Role matched:      20%
Professional tone: 100%

❌ Eval gate: avg 2.20 < 3.5

Cover letter quality: avg 2.2/5 across 3 real job applications