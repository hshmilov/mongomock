#!/bin/bash
# Simple Script to run pylint only on untracked or modified files, print the first one that failed


DIR=$(dirname ${BASH_SOURCE[0]})
PYLINTRC=$DIR/../../pylintrc.txt
EXEMPTFILE=$DIR/../../testing/parallel_tests/pylint_exempt_list.txt

PEP=0
EXIT=1
PARALLEL=0
DELETE=0

function usage {
    echo "usage: git-pylint [-a] [-p] [-d] [P] [-r] [-h]"
    echo "-a --all              Don't stop on first failure print all results"
    echo "-p --parallel         Run all test parallel (requires parallel binary) and -a for now"
    echo "-d --delete           Auto delete files from exemptfile when needed"
    echo "-P --pep              Run autopep8 before checking with pylint"
    echo "-r --all-flags        Use all flags"
    exit 0
}
for i in "$@"
do
case $i in
    -h|--help)
    usage
    shift 
    ;;
    -a|--all)
    EXIT=0
    shift
    ;;
    -p|--parallel)
    PARALLEL=1
    shift
    ;;
    -d|--delete)
    DELETE=1
    shift
    ;;
    -P|--pep)
    PEP=1
    shift
    ;;
    -r|--all-falgs)
    PEP=1
    EXIT=0
    DELETE=1
    PARALLEL=1
    shift
    ;;
    *)
    echo "usage: git-pylint [-a] [-p] [-d] [P] [-r] [-h]"
    exit 0
    ;;
esac
done

function error_and_exit {
    echo $1 >&2
    exit 1
}

function exit_if_needed {
    if [ $EXIT -eq 1 ]; then
        exit 1
    fi
}

PREFIX="bash -c"

# check that we have parallel binary and fix prefix
if [ $PARALLEL -eq 1 ]; then
    sem 2>/dev/null || error_and_exit "missing 'sem' binary (apt-get install parallel)"
    PREFIX="sem -j8"
    
    if [ $EXIT -eq 1 ]; then
        error_and_exit "-p requires -a for now"
        # TODO: -p without -a should be implemented using the following line, but it doesn't work for me yet
        #    PREFIX="sem -j8 --halt 2 --termseq KILL"
    fi
fi


for file in `git diff --cached --name-only; git diff --name-only; git ls-files --other --exclude-standard`; do 
    if [ ${file: -3} == ".py" ]; then

        # handle pep
        if [ $PEP -eq 1 ]; then
            autopep8 --max-line-length 120 --in-place $file
            autopep8 --select=E722 --aggressive --in-place $file
        fi

        # handle delete 
        if [ $DELETE -eq 1 ]; then
            INEXEMPTCMD="grep -v $file $EXEMPTFILE > $EXEMPTFILE.temp && mv $EXEMPTFILE.temp $EXEMPTFILE && echo [*] Removed $file from excemptfile"
        else
            INEXEMPTCMD="echo [-] $file in exemptfile"
        fi
        
        # if file in exemptfile we need to check if it valid and print error if need to remove it
        if grep -q $file $EXEMPTFILE; then 
            $PREFIX "pylint --rcfile=$PYLINTRC $file 2>&1 >/dev/null && $INEXEMPTCMD && exit 1 || echo \"[*] $file in exempt - skipped\"; exit 0 " || exit_if_needed
        else
            $PREFIX "pylint --rcfile=$PYLINTRC $file 2>&1 >/dev/null && echo \"[+] $file\" && exit 0 || echo \"[-] $file\"; exit 1 " || exit_if_needed
        fi
    fi
done

# if parallel wait for all
if [ $PARALLEL -eq 1 ]; then
    sem --wait
fi
