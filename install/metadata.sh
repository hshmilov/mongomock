#!/usr/bin/env bash

echo "Build date: "
date
echo "Hash:"
git log --oneline -1 --format=%H
echo "Ref names:"
git log --oneline -1 --format=%D
echo "Committer date and subject"
git log --oneline -1 --format=%ci%n%s