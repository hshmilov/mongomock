# Development Environment Setup #

This basic bash scripts sets up a development environment on a linux system.
It creates a dir named axonius under the home directory (Of the current user).
It uses the github.com api to fork all the necessary repos from Axonius github org.
It clones all the repos to the created directory.
It sets remotes to axonius for all the cloned repos (named upstream).

### How it works ###
Uses the github GraphQL qpi to fork and then git client to clone locally (expects ssh keys to be setup beforehand).

### How to use ###
After setting up the ssh keys with your github user.
run axonius_env_up.sh


### Optional ###
mac_install.sh installs (in this specific order):
 - Homebrew
 - google-chrome
 - virtualbox + vbox extension pack
 - spectacle
 - iterm2
 - pycharm
 - zsh + zsh-completions
 - httpie
 - python3
 - oh-my-zsh
It uses Homebrew to preform all the installations (after Homebrew itself of course) so notice that all the versions are bound to Homebrew versions.