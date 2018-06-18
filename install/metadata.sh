#!/usr/bin/env bash

version=$1
build_date=$(date)
hash=$(git log --oneline -1 --format=%H)
ref_name=$(git log --oneline -1 --format=%D)
commit_date=$(git log --oneline -1 --format=%ci)
commit_subject=$(git log --oneline -1 --format=%s)
echo -e "{\"Version\":\""$version"\", \"Build Date\":\""$build_date"\", \"Commit Hash\":\""$hash"\", \"Git Reference\":\""$ref_name"\", \"Commit Date\":\""$commit_date"\", \"Commit Subject\":\""$commit_subject"\"}"