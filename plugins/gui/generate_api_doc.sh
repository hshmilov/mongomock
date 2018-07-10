#!/usr/bin/env bash
set -e

swagger-codegen validate -i swagger.yaml
swagger-codegen generate -i swagger.yaml -l swagger
swagger2pdf -s swagger.json