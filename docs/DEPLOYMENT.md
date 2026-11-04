# Deploy on Streamlit Community Cloud (free)

1. Push this project to a **public GitHub repo** (confirm `.env` is NOT committed: `git ls-files | grep -i env`).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app** > choose your repo, branch `main`, main file `app.py`.
4. Open **Advanced settings > Secrets** and paste:
   ```toml
   GROQ_API_KEY = "your_new_groq_key"
   ```
5. Click **Deploy**. The first start takes a few minutes (installs ChromaDB, downloads the embedding model on first upload).
6. Copy the live URL into your README and submission form.

Notes
- `pysqlite3-binary` in `requirements.txt` fixes the common ChromaDB "sqlite3 too old" error on Linux hosts.
- Storage is temporary: indexed documents and tracked jobs reset when the app restarts. Re-load the sample data for demos.
- If the app sleeps, open the URL once before recording or presenting.
