#!/usr/bin/env bash
# Run this on the VM after copying the repo.
# Prereqs on VM: nothing besides curl (for k3s) and kubectl from k3s install.

set -euo pipefail

# Load .env if present (for OPENAI_API_KEY, GROQ_API_KEY, PROJECT_ID, REGION, etc.)
if [ -f ".env" ]; then
  set -o allexport
  # shellcheck disable=SC1091
  source ".env"
  set +o allexport
fi

PROJECT_ID="${PROJECT_ID:-andela-dg}"
REGION="${REGION:-us-central1}"
REPO="${REPO:-study-buddy-repo}"
IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/study-buddy:latest}"
REPO_URL="${REPO_URL:-https://github.com/yuvanist/ai-study-buddy}"
OPENAI_API_KEY="${OPENAI_API_KEY:?Set OPENAI_API_KEY (or put in .env)}"
GROQ_API_KEY="${GROQ_API_KEY:?Set GROQ_API_KEY (or put in .env)}"

echo "[info] Using IMAGE=$IMAGE"

cd ~/ai-study-buddy

# Install k3s (single-node Kubernetes)
curl -sfL https://get.k3s.io | sh -
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Patch image
sed -i "s#gcr.io/PROJECT_ID/study-buddy:latest#${IMAGE}#g" k8s/streamlit-deployment.yaml

# Deploy app + secrets
kubectl apply -f k8s/streamlit-deployment.yaml
kubectl -n study-buddy create secret generic study-buddy-secrets \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --from-literal=GROQ_API_KEY="$GROQ_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# Install Argo CD and expose via NodePort 30443
kubectl create namespace argocd || true
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd patch svc argocd-server -p \
  '{"spec":{"type":"NodePort","ports":[{"name":"https","port":443,"targetPort":8080,"nodePort":30443}]}}' || true

# Update Argo app repoURL if needed
sed -i "s#https://github.com/REPLACE_WITH_YOUR_REPO/ai-study-buddy.git#${REPO_URL}.git#g" k8s/argo-app.yaml

kubectl apply -f k8s/argo-app.yaml

echo "[info] Argo admin password:"
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

echo ""
echo "App:    http://$(curl -s ifconfig.me):30080"
echo "Argo:   https://$(curl -s ifconfig.me):30443 (user: admin, pass above)"

