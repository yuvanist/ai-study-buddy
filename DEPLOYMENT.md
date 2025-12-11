# Deployment Guide (GCP e2-micro, k3s, Argo CD required)

> All shell commands assume `conda activate andela` first, e.g.  
> `conda activate andela && <command>`

Goal: single-node k3s on a small VM (default e2-small, 10GB), NodePort for the app, Argo CD for GitOps. Defaults: PROJECT_ID `andela-dg`, REGION `us-central1`.

## One-liner flow with scripts
- Put `.env` at repo root with at least: `OPENAI_API_KEY=...`, `GROQ_API_KEY=...` (optional overrides: PROJECT_ID, REGION, ZONE, REPO, VM_NAME, REPO_URL).
- Local (build/push + VM create/copy): `bash scripts/local_deploy.sh`
- On VM (k3s install, deploy app, Argo CD install/expose, apply Argo app): `bash ~/ai-study-buddy/scripts/vm_bootstrap.sh`

Defaults in scripts:
- PROJECT_ID: `andela-dg`
- REGION: `us-central1`
- ZONE: `us-central1-a`
- VM type: `e2-micro` (10GB disk)

Before running `vm_bootstrap.sh` on the VM, export:
```bash
export OPENAI_API_KEY=<your-openai-key>
export GROQ_API_KEY=<your-groq-key>
```

## Manual reference (if you prefer step-by-step)
### Local
Use `scripts/local_deploy.sh` as reference: it sets project, creates Artifact Registry, builds/pushes the image, creates the e2-micro VM + firewall, and copies the repo to the VM.

### VM
Use `scripts/vm_bootstrap.sh` as reference: installs k3s, patches the image, applies the app manifests, creates secrets, installs Argo CD (NodePort 30443), updates `k8s/argo-app.yaml` repoURL (defaults to https://github.com/yuvanist/ai-study-buddy.git), and applies the Argo app.

## Endpoints
- App: `http://<VM_EXTERNAL_IP>:30080`
- Argo CD: `https://<VM_EXTERNAL_IP>:30443` (user `admin`, password from secret above)

If you prefer port-forward instead of NodePorts:
```bash
kubectl -n study-buddy port-forward svc/study-buddy 8501:80
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

