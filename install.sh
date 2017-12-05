#!/usr/bin/env bash


echo Removing all containers and volumes..
docker rm -f $(docker ps -a -q)
docker volume rm $(docker volume ls -q)

echo Removing all images starting with axonius/*..
docker rmi $(docker images -q --filter=reference='axonius/*')

echo Pulling axonius-base-image and building axonius/axonius-libs
docker login -u axoniusdockerreadonly -p 48GguwDPOQbMNYj08Pmb
docker pull axonius/axonius-base-image
docker build -t axonius/axonius-libs plugins/axonius-libs

echo Installing database...
docker-compose -f devops/systemization/database/docker-compose.yml -f devops/systemization/database/docker-compose.prod.yml up -d

echo Installing core...
docker-compose -f plugins/core/docker-compose.yml -f plugins/core/docker-compose.prod.yml up -d

echo Installing aggregator...
docker-compose -f plugins/aggregator-plugin/docker-compose.yml -f plugins/aggregator-plugin/docker-compose.prod.yml up -d

echo Installing ad...
docker-compose -f adapters/ad-adapter/docker-compose.yml -f adapters/ad-adapter/docker-compose.prod.yml up -d

echo Installing aws...
docker-compose -f adapters/aws-adapter/docker-compose.yml -f adapters/aws-adapter/docker-compose.prod.yml up -d

echo Installing esx...
docker-compose -f adapters/esx-adapter/docker-compose.yml -f adapters/esx-adapter/docker-compose.prod.yml up -d

echo Installing gui...
docker-compose -f plugins/gui/docker-compose.yml -f plugins/gui/docker-compose.prod.yml up -d

echo Done.