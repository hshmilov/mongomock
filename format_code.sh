#!/usr/bin/env bash
git ls-files | grep "\.py$" | xargs autopep8 --max-line-length 120 --in-place
git ls-files | grep "\.py$" | xargs autopep8 --select=E722 --aggressive --in-place
