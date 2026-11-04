#!/bin/bash
set -e

PORT="${X_ZOHO_CATALYST_LISTEN_PORT:-8501}"
echo "Starting Career Copilot on port $PORT..."

# Determine python command
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    PY="python"
fi

exec $PY -m streamlit run app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false
