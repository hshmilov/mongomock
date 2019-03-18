import time

from devops.CI.scripts.axonius_builds_context.axoniusbuilds import builds


def main():
    ami = ''

    with builds.Instance('test_master', ami=ami) as master, builds.Instance(
            'test_node', ami=ami) as node:
        ready = False
        while ready is False:
            time.sleep(60)
            master_state = master.ssh('tail -n2 /home/ubuntu/builds_log/install.log | head -n -1')
            node_state = node.ssh('tail -n2 /home/ubuntu/builds_log/install.log | head -n -1')
            ready = master_state[0] == 'final tweeks\n' and node_state[0] == 'final tweeks\n'

        key = master.ssh('cat /home/ubuntu/cortex/shared_readonly_files/.__key')
        node.ssh(
            f'cd /home/ubuntu/cortex; ./devops/scripts/instances/setup_node.sh {master.ip} {key[0][:-1]} Test_Node',
            timeout=60 * 5)


if __name__ == '__main__':
    main()
