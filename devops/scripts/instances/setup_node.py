#!/usr/bin/env python3
import sys

if __name__ == '__main__':
    from devops.scripts.instances.setup_node_logic import logic_main

    logic_main(sys.argv[1:])
