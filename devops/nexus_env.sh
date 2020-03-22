#!/bin/bash

if [ -z "`curl -s nexus.axonius.lan`" ]; then
  export NEXURL=nexus-public.axonius.com
else
  export NEXURL=nexus.axonius.lan
fi

