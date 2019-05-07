#!/usr/bin/env python3
import os

CORTEX_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..'))
VENV_PATH = os.path.join(CORTEX_PATH, 'venv')

print('Activating venv!')
activate_this_file = os.path.join(VENV_PATH, 'bin', 'activate_this.py')
# pylint: disable=exec-used
exec(open(activate_this_file).read(), dict(__file__=activate_this_file))
print('Venv activated!')

if __name__ == '__main__':
    from devops.scripts.instances.setup_node_logic import logic_main

    logic_main()
