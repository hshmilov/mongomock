#!/usr/bin/env bash
echo "Logging in to docker..."
(
source ./login.sh
rm -rf ./login.sh
)

cd ..

echo "Building all..."
(
docker rm -f $(docker ps -a -q)
docker volume rm $(docker volume ls -q)
docker rmi $(docker images -q --filter=reference='axonius/*')
docker pull axonius/axonius-base-image
docker build -t axonius/axonius-libs plugins/axonius-libs
docker build -t axonius/core plugins/core
docker build -t axonius/aggregator plugins/aggregator-plugin
#docker build -t axonius/watch-service plugins/watch-service
docker build -t axonius/gui plugins/gui
docker build -t axonius/ad-adapter adapters/ad-adapter
docker build -t axonius/aws-adapter adapters/aws-adapter
docker build -t axonius/esx-adapter adapters/esx-adapter
docker build -t axonius/epo-adapter adapters/epo-adapter
)

echo "Removing anything irrelevant.."
(
docker logout
rm -rf .git* ./testing .idea* .cache* *.bat *.sh ./devops */*/tests
history -c
history -w
)

echo "Running all..."
(
docker-compose -f infrastructures/database/docker-compose.yml -f infrastructures/database/docker-compose.prod.yml up -d
docker-compose -f plugins/core/docker-compose.yml -f plugins/core/docker-compose.prod.yml up -d
docker-compose -f plugins/aggregator-plugin/docker-compose.yml -f plugins/aggregator-plugin/docker-compose.prod.yml up -d
docker-compose -f adapters/ad-adapter/docker-compose.yml -f adapters/ad-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/aws-adapter/docker-compose.yml -f adapters/aws-adapter/docker-compose.prod.yml up -d
docker-compose -f adapters/esx-adapter/docker-compose.yml -f adapters/esx-adapter/docker-compose.prod.yml up -d
docker-compose -f plugins/gui/docker-compose.yml -f plugins/gui/docker-compose.prod.yml up -d
)

echo "Done."