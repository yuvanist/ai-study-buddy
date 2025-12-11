#!/usr/bin/env bash
# Usage: bash scripts/local_deploy.sh
# Prereqs: gcloud, docker, and conda env `andela` available locally.
# Defaults are tuned for lowest-cost deployment: project andela-dg, region us-central1, VM e2-micro.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load .env if present for overrides (PROJECT_ID, REGION, etc.)
if [ -f "$ROOT_DIR/.env" ]; then
  set -o allexport
  # shellcheck disable=SC1090
  source "$ROOT_DIR/.env"
  set +o allexport
fi

# ---- Config (override via env) ----
PROJECT_ID="${PROJECT_ID:-andela-dg}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-a}"
REPO="${REPO:-study-buddy-repo}"
VM_NAME="${VM_NAME:-study-buddy-vm}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-small}"
IMAGE="${IMAGE:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/study-buddy:latest}"
SRC_DIR="${SRC_DIR:-$ROOT_DIR}"

echo "[info] Using PROJECT_ID=${PROJECT_ID}, REGION=${REGION}, ZONE=${ZONE}, IMAGE=${IMAGE}"

# ---- Local build & push ----
gcloud config set project "$PROJECT_ID"
gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION" || true
gcloud auth configure-docker "${REGION}-docker.pkg.dev"

docker build -t "$IMAGE" "$SRC_DIR"
docker push "$IMAGE"

# ---- VM create (e2-micro) + firewall ----
gcloud compute instances create "$VM_NAME" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=10GB \
  --tags=study-buddy || true

gcloud compute firewall-rules create study-buddy-nodes \
  --allow=tcp:30080,tcp:30443 \
  --target-tags=study-buddy || true

# ---- Copy repo + VM bootstrap script ----
gcloud compute scp --recurse "$SRC_DIR" "${VM_NAME}:/home/${USER}/ai-study-buddy" --zone="$ZONE"

echo ""
echo "[next] SSH into the VM and run: bash ~/ai-study-buddy/scripts/vm_bootstrap.sh"
echo "      Remember to export OPENAI_API_KEY and GROQ_API_KEY on the VM before running it."

