#!/usr/bin/env bash
set -e
exit 0
cd "$(dirname "$0")"

echo "Installing golang (bandicoot) requirements"
cd bandicoot
go mod vendor
cd ..
echo "Done golang (bandicoot) requirements"
