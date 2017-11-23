#!/usr/bin/env bash

docker rmi $(docker images -q --filter=reference='axonius/*')

echo "Build axoinius libs"
(
docker stop axonius/core axonius/aggregator
docker rmi axonius/axonius-libs axonius/core axonius/aggregator
cd plugins/axonius-libs
docker build --no-cache -t axonius/axonius-libs .
)

echo "Create venv"
./create_venv.sh
