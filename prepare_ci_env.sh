#!/usr/bin/env bash

echo "Build axoinius libs"
(
docker rmi axonius/axonius-libs
cd plugins/axonius-libs
docker build -t axonius/axonius-libs .
)

echo "Create venv"
./create_venv.sh
