#!/usr/bin/env bash

source env_autogen.sh

if [ "$#" -ne 3 ]; then
    echo "Usage $0 ssh/stunnel public_host_port local_port"
    exit 0
fi

type=$1
public_host_port=$2
local_port=$3

if [ $1 = "ssh" ]; then
    sshpass -p ${PUBLIC_SSH_HOST_PASSW} ssh -oStrictHostKeyChecking=no -NTR 0.0.0.0:${public_host_port}:localhost:${local_port} ${PUBLIC_SSH_HOST_USER}@${PUBLIC_SSH_HOST_ADDR} -p 443
    exit 0
fi

if [ $1 = "stunnel" ]; then
    sshpass -p ${PUBLIC_SSL_HOST_PASSW} ssh -oStrictHostKeyChecking=no -NTR 0.0.0.0:${public_host_port}:localhost:${local_port} ${PUBLIC_SSL_HOST_USER}@localhost -p ${STUNNEL_LISTEN_PORT}
    exit 0
fi

echo "manual forward can be either ssh or stunnel. Exiting"