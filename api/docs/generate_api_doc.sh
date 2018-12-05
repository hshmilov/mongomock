#!/bin/bash

function error_exit {
    echo "$1" >&2   ## Send message to stderr. Exclude >&2 if you don't want it that way.
    exit "${2:-1}"  ## Return a code specified by $2 or 1 by default.
}

[[ $(type -P "swagger-codegen") ]] || error_exit "swagger-codgen: command not found"
[[ $(type -P "swagger2pdf") ]] || error_exit "swagger2pdf: command not found"

set -e

swagger-codegen validate -i swagger.yaml
swagger-codegen generate -i swagger.yaml -l swagger
swagger2pdf -s swagger.json
