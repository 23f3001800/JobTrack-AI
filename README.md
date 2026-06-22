# JobTrack-AI
autonomous 6-step job application workflow agent — for job seekers


curl -X POST http://localhost:8001/run -H "Authorization: Bearer dev-secret-key" -d '{"job_url":"https://www.ycombinator.com/companies/14-ai/jobs/KoEfdhc-full-stack-engineering-internship-now-and-summer-2026"}'


curl -X POST http://localhost:8000/run \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"job_url":"https://www.ycombinator.com/companies/14-ai/jobs/KoEfdhc-full-stack-engineering-internship-now-and-summer-2026"}'