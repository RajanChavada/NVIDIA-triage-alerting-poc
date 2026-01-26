# Hosting Guide: NVIDIA Triage AI POC

This guide provides instructions for hosting the Streamlit frontend and FastAPI backend without using Docker.

## 1. Environment Preparation

Before hosting, ensure you have the requirements installed:

```bash
pip install -r requirements.txt
```

Ensure your `.env` file is configured with the necessary API keys (e.g., `GOOGLE_API_KEY`).

---

## 2. Hosting Options

### Option A: Streamlit Community Cloud (Easiest for UI)
If your repository is on GitHub (Public or Private), you can host the UI for free.

1. Go to [share.streamlit.io](https://share.streamlit.io).
2. Connect your GitHub repository.
3. Set the Main file path to `streamlit_app.py`.
4. **Crucial**: In the "Advanced Settings" on Streamlit Cloud, add your environment variables:
   - `BACKEND_URL`: URL of your running FastAPI backend.
   - Any other keys from your `.env`.

> [!NOTE]
> Streamlit Cloud only hosts the frontend. You still need a separate place to host the FastAPI backend.

### Option B: Render / Railway (Full Stack)
These platforms can host both Python services easily.

1. **FastAPI Backend**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. **Streamlit Frontend**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`
   - Environment Variable: Set `BACKEND_URL` to the URL provided by your FastAPI service.

### Option C: Virtual Machine (AWS EC2 / NVIDIA Internal VM)
This is the most flexible approach for internal tools.

1. **Clone and Install**:
   ```bash
   git clone <your-repo-url>
   cd NVIDIA-triage-alerting-poc
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run Backend (Background)**:
   ```bash
   # Using nohup or screen/tmux
   nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &
   ```

3. **Run Streamlit (Background)**:
   ```bash
   export BACKEND_URL="http://<vm-ip>:8000"
   nohup streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
   ```

> [!TIP]
> For production-like persistence on a VM, use **PM2** or **systemd** to manage the processes so they restart automatically.

---

## 3. Configuration Summary

| Variable | Description | Default |
| :--- | :--- | :--- |
| `BACKEND_URL` | The full URL where the FastAPI app is reachable | `http://localhost:8000` |
| `GOOGLE_API_KEY` | Required for Gemini AI features | - |
| `DATABASE_URL` | PostgreSQL connection string | (Local SQLite/Dev) |

---

## 4. NVIDIA Specific Clusters
If deploying to internal NVIDIA resources (like Maglev or internal K8s):
- Use the provided `Dockerfile` if the platform supports containers.
- If it's a bare VM, follow **Option C**.
- Ensure internal firewalls allow traffic on ports `8000` (API) and `8501` (UI).
