#!/usr/bin/env bash

source ../../bash_imports.sh

cd ../../
cp ./devops/scripts/host_installation/uploads/ip_wizard/login.c ./infrastructures/host/uploads/
cp ./devops/scripts/host_installation/uploads/ip_wizard/login.py ./infrastructures/host/uploads/
cp ./devops/scripts/host_installation/uploads/nexus-apt ./infrastructures/host/uploads/
cp ./devops/scripts/host_installation/uploads/pip.conf ./infrastructures/host/uploads/
cp ./devops/scripts/host_installation/uploads/weave-2.7.0 ./infrastructures/host/uploads/
cp ./devops/scripts/host_installation/uploads/ZscalerRootCertificate-2048-SHA256.crt ./infrastructures/host/uploads/
cp requirements.txt ./infrastructures/host/uploads/
cp ./libs/axonius-base-image/requirements2.txt ./infrastructures/host/uploads/
cp -r ./api/axoniussdk ./infrastructures/host/
cp -r ./devops/ax_cli ./infrastructures/host/

cd ./infrastructures/host && docker build . -t $DOCKER_NAME
cd ./uploads/ && rm -f login.c login.py nexus-apt pip.conf weave-2.7.0 ZscalerRootCertificate-2048-SHA256.crt requirements.txt requirements2.txt
cd ../ && rm -rf axoniussdk ax_cli