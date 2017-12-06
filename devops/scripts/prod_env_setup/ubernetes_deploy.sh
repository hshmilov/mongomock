#!/usr/bin/env bash

sudo systemctl daemon-reload

sudo hostname $(hostname -f)

export PRIVATE_IP=$(hostname -i)
export AWS_HOST_NAME=$(hostname -f)
export PUBLIC_IP=$(curl http://169.254.169.254/latest/meta-data/public-ipv4)

#### add KUBELET_FLAGS ####

sudo kubeadm init --apiserver-advertise-address=$PUBLIC_IP --apiserver-cert-extra-sans=$PRIVATE_IP --node-name=$AWS_HOST_NAME --pod-network-cidr=10.244.0.0/16

mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')&env.KUBE_PEERS=$PUBLIC_IP"

#### sudo kubeadm join ####

kubectl taint nodes --all node-role.kubernetes.io/master-

kubectl label nodes $AWS_HOST_NAME ax_type=cloud

#kubectl apply -f axonius.yaml
