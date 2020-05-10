#!/usr/bin/env bash

function _wait_for_apt {
    i=0

    until /usr/bin/apt-get "$@"
    do
        ((i=i+1))
        if [ $i -gt 20 ]
        then
            echo "Timeout reached on $@!"
            exit 1
        fi
        echo "Waiting $i..."
        sleep 60
    done

}

# add-apt-repository ppa:longsleep/golang-backports
echo "Adding Golang Repository"
curl -sSk https://nexus.pub.axonius.com/ppa_certs/golang.key | apt-key add -
add-apt-repository "deb https://axoniusreadonly:7wr7E6kfttdVgn5e@nexus.pub.axonius.com/repository/golang $(lsb_release -cs) main"
_wait_for_apt update
_wait_for_apt install -yq golang-go