#!/bin/bash
DIR=$(dirname ${BASH_SOURCE[0]})

function main {
    mkdir api
    ./generate_api_doc.sh || return 1
    ./generate_fields_for_api.py || return 1
    mv ./device_fields.py ./api
    mv ./user_fields.py ./api
    mv api.pdf ./api
    cp -r ../axoniussdk/ ./api/
    mkdir ./api/examples
    cp ../examples/*.py ./api/examples
    tar -cJvf api.tar.xz ./api
    return 0
}

function cleanup {
    rm -rf api
    rm -f .swagger-codegen-ignore
    rm -rf .swagger-codegen/
    rm -f README.md
    rm -f swagger.json
    rm -f device_fields.py
    rm -f user_fields.py
    rm -f api.pdf
}

function cleanup_all {
    cleanup
    rm -f api.tar.xz
}

pushd $DIR
cleanup_all
    main || cleanup_all && cleanup
popd
