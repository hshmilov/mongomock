#!/usr/bin/env bash
docker-compose down
set -e
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up -d