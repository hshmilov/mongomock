#!/usr/bin/env bash

cd "$(dirname "$0")"
cd ./src/frontend

rm -rf dist
rm -rf node_modules

npm install
npm run dev-build

docker-compose build
