#!/bin/bash
set -ex

# Install k3s
curl -sfL https://get.k3s.io | sh -
sleep 10
chmod 644 /etc/rancher/k3s/k3s.yaml
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Wait for k3s to be ready
kubectl wait --for=condition=Ready node --all --timeout=120s

# Clone repo
cd /root
git clone https://github.com/yuvanist/ai-study-buddy.git
cd ai-study-buddy

# Deploy app
kubectl apply -f k8s/streamlit-deployment.yaml

# Install Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for argocd-server to be created then patch
sleep 30
kubectl -n argocd patch svc argocd-server -p '{"spec":{"type":"NodePort","ports":[{"name":"https","port":443,"targetPort":8080,"nodePort":30443}]}}'

# Apply Argo app
kubectl apply -f k8s/argo-app.yaml

# Log completion
echo "STARTUP COMPLETE" > /root/startup-done.txt
