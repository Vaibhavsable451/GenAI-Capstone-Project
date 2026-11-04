#!/bin/sh
PORT="${X_ZOHO_CATALYST_LISTEN_PORT:-9000}"
streamlit run app.py --server.address 0.0.0.0 --server.port "$PORT" --server.headless true
