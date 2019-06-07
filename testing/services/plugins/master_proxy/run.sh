#!/bin/bash

###############################################################################
# Name:         run.sh
# Author:       Daniel Middleton <daniel-middleton.com>
# Description:  Used as ENTRYPOINT from Tinyproxy's Dockerfile
# Usage:        See displayUsage function
###############################################################################

# Global vars
PROG_NAME='DockerTinyproxy'
PROXY_CONF='/etc/tinyproxy/tinyproxy.conf'
TAIL_LOG="/home/axonius/logs/master-proxy.rawtext.log"

# Usage: screenOut STATUS message
screenOut() {
    timestamp=$(date +"%H:%M:%S")

    if [ "$#" -ne 2 ]; then
        status='INFO'
        message="$1"
    else
        status="$1"
        message="$2"
    fi

    echo -e "[$PROG_NAME][$status][$timestamp]: $message"
}

# Usage: checkStatus $? "Error message" "Success message"
checkStatus() {
    case $1 in
        0)
            screenOut "SUCCESS" "$3"
            ;;
        1)
            screenOut "ERROR" "$2 - Exiting..."
            exit 1
            ;;
        *)
            screenOut "ERROR" "Unrecognised return code."
            ;;
    esac
}

displayUsage() {
    echo
    echo '  Usage:'
    echo "      docker run -d --name='tinyproxy' -p <Host_Port>:8888 dannydirect/tinyproxy:latest <ACL>"
    echo
    echo "      - Set <Host_Port> to the port you wish the proxy to be accessible from."
    echo "      - Set <ACL> to 'ANY' to allow unrestricted proxy access, or one or more spece seperated IP/CIDR addresses for tighter security."
    echo
    echo "      Examples:"
    echo "          docker run -d --name='tinyproxy' -p 6666:8888 dannydirect/tinyproxy:latest ANY"
    echo "          docker run -d --name='tinyproxy' -p 7777:8888 dannydirect/tinyproxy:latest 87.115.60.124"
    echo "          docker run -d --name='tinyproxy' -p 8888:8888 dannydirect/tinyproxy:latest 10.103.0.100/24 192.168.1.22/16"
    echo
}

stopService() {
    screenOut "Checking for running Tinyproxy service..."
    if [ "$(pidof tinyproxy)" ]; then
        screenOut "Found. Stopping Tinyproxy service for pre-configuration..."
        killall tinyproxy
        checkStatus $? "Could not stop Tinyproxy service." \
                       "Tinyproxy service stopped successfully."
    else
        screenOut "Tinyproxy service not running."
    fi
}

parseAccessRules() {
    list=''
    for ARG in $@; do
        line="Allow\t$ARG\n"
        list+=$line
    done
    echo "$list" | sed 's/.\{2\}$//'
}

startService() {
    screenOut "Starting Tinyproxy service..."
    /usr/sbin/tinyproxy
    checkStatus $? "Could not start Tinyproxy service." \
                   "Tinyproxy service started successfully."
}

tailLog() {
    screenOut "Tailing Tinyproxy log..."
    tail -f $TAIL_LOG
    checkStatus $? "Could not tail $TAIL_LOG" \
                   "Stopped tailing $TAIL_LOG"
}

# Check args
if [ "$#" -lt 1 ]; then
    displayUsage
    exit 1
fi
# Start script
echo && screenOut "$PROG_NAME script started..."
# Stop Tinyproxy if running
stopService
# Parse ACL from args
export rawRules="$@" && parsedRules=$(parseAccessRules $rawRules) && unset rawRules
# Start Tinyproxy
startService
# Tail Tinyproxy log
tailLog
# End
screenOut "$PROG_NAME script ended." && echo
exit 0
