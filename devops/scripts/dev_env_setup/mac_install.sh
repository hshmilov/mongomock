#!/usr/bin/env bash

/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

brew tap caskroom/versions

brew cask install docker google-chrome virtualbox virtualbox-extension-pack spectacle iterm2 pycharm #sublime-text

brew install zsh zsh-completions httpie python3

curl -L https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh | sh

chsh -s /usr/local/bin/zsh
