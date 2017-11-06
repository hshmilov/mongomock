#!/usr/bin/env bash

echo "Build axoinius libs"
(
docker rmi axonius-libs
cd plugins/axonius-libs
docker build -t axonius-libs .
)

echo "Create venv"
./create_venv.sh
