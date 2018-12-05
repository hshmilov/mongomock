#!/bin/bash
DIR=$(dirname ${BASH_SOURCE[0]})

pushd $DIR
mkdir api
./generate_api_doc.sh
rm -f .swagger-codegen-ignore
rm -rf .swagger-codegen/
rm -f README.md
rm -f swagger.json
mv api.pdf ./api

cp -r ../axoniussdk/ ./api/

mkdir ./api/examples
cp ../examples/*.py ./api/examples

cd ./api
../generate_fields_for_api.py
cd ..
tar -cJvf api.tar.xz ./api/*
popd
