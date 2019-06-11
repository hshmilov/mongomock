"""
Fixes https://axonius.atlassian.net/browse/AX-4207
Note - was written super fast on 3:22 am so code looks like that. Still putting for the protocol
"""
import sys
import subprocess
import docker


def run_shell(shell):
    return subprocess.check_output(shell, shell=True).decode('utf-8')


def main():
    try:
        _, mode = sys.argv  # pylint: disable=unbalanced-tuple-unpacking
    except Exception:
        print(f'Usage: {sys.argv[0]} dry/wet')
        return -1

    docker_client = docker.DockerClient('unix:///var/run/weave/weave.sock')

    # First, identify bad nodes. We assume that ad is good since it was there since the beginning of the node,
    # and the bug occurs only on new adapters.
    node_id_output = run_shell('docker exec active-directory-adapter cat ../plugin_volatile_config.ini | grep node_id')
    if 'node_id = ' not in node_id_output:
        raise ValueError(f'Bad AD plugin_volatile_config: {node_id_output}')
    current_node_id = node_id_output.split('=')[1].strip()
    print('current node id: ' + current_node_id)

    # Now, identify all adapters which are for some reason not identifying themselves as being on this node.
    axonius_containers = [container for container in docker_client.containers.list()
                          if 'axonius' in str(container.image).lower()]
    i = 0
    for container in axonius_containers:
        exit_code, output = container.exec_run('cat ../plugin_volatile_config.ini')
        assert exit_code == 0, f'Error for {container.name}: {output}'
        output = output.decode('utf-8')
        assert 'node_id = ' in output, f'Bad output {output}'

        if current_node_id not in output:
            i += 1
            print(f'{i}. Found container on a different node id: {container.name}')

            adapter_name = container.name[:-8].replace('-', '_')
            wet_command = f'sed -i "s/node_id.*/node_id = {current_node_id}/" ../plugin_volatile_config.ini'
            if mode == 'wet':
                print(f'Wet command: {wet_command}')
                exit_code, output = container.exec_run(wet_command)
                assert exit_code == 0, f'Error for {container.name}: {output}'
                output = output.decode('utf-8')
                print(output)
                print(run_shell(f'/home/ubuntu/cortex/axonius.sh adapter {adapter_name} up --restart --prod'))

    return 0


if __name__ == '__main__':
    exit(main())
