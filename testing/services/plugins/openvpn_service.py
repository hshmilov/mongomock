import subprocess

import docker

from scripts.instances.instances_consts import VPN_DATA_DIR
from scripts.instances.instances_consts import TUNNEL_RESOLV_FILE_HOST_PATH
from scripts.instances.instances_consts import VPNNET_NETWORK

from axonius.consts.system_consts import NODE_MARKER_PATH
from services.docker_service import DockerService
from services.ports import DOCKER_PORTS

OPENVPN_CONTAINER_NAME = 'openvpn-service'
REQUIRED_KERNEL_MODULES = ['iptable_nat', 'nf_conntrack_ipv4', 'nf_nat_ipv4', 'nf_nat']
OPENVPN_SETUP_COMMANDS = [
    'route del default',
    'route add default gw 192.167.255.1 dev tun0',
    'iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE',
    'iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT',
    'iptables -A INPUT -i eth0 -j ACCEPT',
    'iptables -P INPUT DROP'
]


class OpenvpnService(DockerService):
    # pylint: disable=line-too-long
    def start(self, *args, **kwargs):  # pylint: disable=arguments-differ
        try:
            TUNNEL_RESOLV_FILE_HOST_PATH.touch()
        except FileNotFoundError:
            # Not supposed to run
            return
        if NODE_MARKER_PATH.is_file():
            print(f'openvpn should not run on node')
        else:
            super().start(*args, extra_flags=['--cap-add=NET_ADMIN'], expose_port=True, **kwargs)

            client = docker.from_env()
            container = client.containers.get(OPENVPN_CONTAINER_NAME)
            try:
                for cmd in OPENVPN_SETUP_COMMANDS:
                    assert container.exec_run(privileged=True, cmd=cmd).exit_code == 0

                # Make sure the required kernel modules are loaded
                container_lsmod = container.exec_run('lsmod').output.decode('utf-8')
                for kernel_module in REQUIRED_KERNEL_MODULES:
                    try:
                        assert kernel_module in container_lsmod
                    except AssertionError:
                        print(f'Kernel module: {kernel_module} is not loaded in the container!!!')
            except AssertionError as e:
                print(f'Error while executing commands on openvpn-service container: {str(e)}')
            except subprocess.CalledProcessError:
                print('Error while executing commands on host machine in openvpn setup')
            except Exception as err:
                print(f'Unknown error while executing commands on openvpn-service container {str(err)}')

    def is_up(self, *args, **kwargs):
        print(f'openvpn started ok')
        return True

    def __init__(self):
        super().__init__(OPENVPN_CONTAINER_NAME, service_dir='services/plugins/openvpn_service')

    @property
    def volumes_override(self):
        return [f'{VPN_DATA_DIR}:/etc/openvpn']

    @property
    def docker_network(self):
        return VPNNET_NETWORK

    @property
    def is_unique_image(self):
        return True

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[OPENVPN_CONTAINER_NAME], DOCKER_PORTS[OPENVPN_CONTAINER_NAME])]
