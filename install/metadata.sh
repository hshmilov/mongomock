#!/usr/bin/env bash

version=$1
build_date=$(date)
hash=$(git log --oneline -1 --format=%H)
commit_date=$(git log --oneline -1 --format=%ci)
echo -e "{\"Version\":\""$version"\", \"Build Date\":\""$build_date"\", \"Commit Hash\":\""$hash"\", \"Commit Date\":\""$commit_date"\"}"