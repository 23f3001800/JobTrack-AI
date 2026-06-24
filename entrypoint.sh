#!/bin/bash
# ============================================================
# JobTrack AI — Docker Entrypoint
# ============================================================
# This script runs before the main process starts.
# It initializes the database (seeds admin user) and then
# exec's into the main command (uvicorn).
#
# WHY an entrypoint script instead of CMD?
# CMD runs a single command. We need to:
# 1. Initialize the database (seed admin)
# 2. THEN start the server
# exec replaces this shell with uvicorn (PID 1 = correct signals)
# ============================================================

set -e

echo "🚀 JobTrack AI — Starting up..."
echo ""

# Initialize database and seed admin user
python -m db.init_db

echo ""
echo "🌐 Starting API server on port ${PORT:-8000}..."
echo ""

# exec replaces shell with uvicorn so it receives SIGTERM directly
exec "$@"
