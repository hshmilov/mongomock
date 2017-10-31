#!/bin/bash

declare -a repo_list=("axonius-libs" "core" "infrastructures" "aggregator-plugin" "gui")

ssh -T git@github.com > /dev/null

if [ $? -eq 1 ]
then
  echo "Github ssh key is configured succesfully."
else
  echo "Github ssh key is not configured. please configure it and run again!" >&2
  exit 1
fi

read -p "Enter Github Username: " github_username
read -s -p "Enter Password: " github_password

# Sets up a work directory
echo "Setting up axonius directory under home."
mkdir ~/axonius
cd ~/axonius

# Forks all the necessary repos
echo "Forking all necessary repos from axonius github to current ssh configured user."
for current_repo in "${repo_list[@]}"
do
    curl -u $github_username:$github_password -X POST https://api.github.com/repos/Axonius/$current_repo/forks > /dev/null
done

# Waiting for asynchronous fork operations to finish
echo "Waiting for asynchronous fork operations to finish."
sleep 30

# Clones all the necessary repos from users fork
for current_repo in "${repo_list[@]}"
do
    git clone git@github.com:$github_username/$current_repo.git --branch develop > /dev/null
    if [ $? -ne 0 ]
    then
        git clone git@github.com:$github_username/$current_repo.git > /dev/null
    fi

    cd ~/axonius/$current_repo
    git remote add upstream git@github.com:Axonius/$current_repo.git
    cd ~/axonius/
done
