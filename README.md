# AI Study Buddy (Streamlit + Agno)

Agno-powered Streamlit study buddy with Groq/OpenAI model selection, personas, structured outputs, and TXT export. Containerized with k3s manifests and Argo CD for GitOps deployment.

## Local run
```bash
conda activate andela
streamlit run app.py
```
Provide `OPENAI_API_KEY` / `GROQ_API_KEY` in `.env` or via the sidebar.

## Container build & push (local)
- Put `.env` at repo root with `OPENAI_API_KEY`, `GROQ_API_KEY` (optional: PROJECT_ID, REGION, ZONE, REPO, VM_NAME, REPO_URL).  
- Then run:
```bash
conda activate andela
bash scripts/local_deploy.sh
```

## Deploy on VM (k3s + Argo CD)
```bash
gcloud compute ssh study-buddy-vm --zone=us-central1-a
cd ~/ai-study-buddy
bash scripts/vm_bootstrap.sh
```

Argo UI: `https://<VM_EXTERNAL_IP>:30443` (user `admin`, password from command above)  
App: `http://<VM_EXTERNAL_IP>:30080`