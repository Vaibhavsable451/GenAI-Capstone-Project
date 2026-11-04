# Deployment Guide

## 1. Deploy on Zoho Catalyst AppSail

### Why "Execution failed. Please check the startup command or port" happens:
- **Wrong startup command:** AppSail by default tries running `python main.py` or `python app.py`. Streamlit apps cannot be run with plain `python app.py`—they immediately exit because Streamlit requires `streamlit run app.py`.
- **Port mismatch:** AppSail expects traffic on port `9000` (passed dynamically via `$X_ZOHO_CATALYST_LISTEN_PORT`), but default Streamlit listens on `8501`.
- **Missing dependencies:** AppSail does not run `pip install -r requirements.txt` unless specified as a build command or in `app-config.json`.
- **Insufficient memory:** ChromaDB + Streamlit require at least 512 MB to 1024 MB RAM. The default 256 MB will cause an out-of-memory (OOM) crash.

### AppSail Configuration in Zoho Catalyst Console:
1. Go to [Zoho Catalyst Console](https://console.catalyst.zoho.com/) > Select your project.
2. Under **Serverless / Compute**, open **AppSail** > select **career-copilot**.
3. Open **Configuration / Settings**:
   - **Stack / Runtime:** `Python 3.11`
   - **Startup Command:** `bash start.sh`
   - **Port:** `9000`
   - **Memory:** `1024 MB` (or at least `512 MB`)
   - **Build Command:** `pip install -r requirements.txt`
4. Under **Environment Variables**, add:
   - `GROQ_API_KEY`: `your_groq_api_key_here`
   - `X_ZOHO_CATALYST_LISTEN_PORT`: `9000`
5. Click **Save** and trigger a **Redeploy**.

---

## 2. Deploy on Streamlit Community Cloud (Free Alternative)

1. Push this project to a **public GitHub repo** (confirm `.env` is NOT committed: `git ls-files | grep -i env`).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app** > choose your repo, branch `main`, main file `app.py`.
4. Open **Advanced settings > Secrets** and paste:
   ```toml
   GROQ_API_KEY = "your_new_groq_key"
   ```
5. Click **Deploy**. The first start takes a few minutes (installs ChromaDB, downloads the embedding model on first upload).
6. Copy the live URL into your README and submission form.

### Notes
- `pysqlite3-binary` in `requirements.txt` fixes the common ChromaDB "sqlite3 too old" error on Linux hosts.
- Storage is temporary: indexed documents and tracked jobs reset when the app restarts. Re-load the sample data for demos.
- If the app sleeps, open the URL once before recording or presenting.
