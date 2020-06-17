import os

import docker

from scripts.instances.network_utils import get_tunnel_subnet_ip_rage, DOCKER_TUNNEL_INTERFACE_NAME
from axonius.consts.system_consts import TUNNEL_NETWORK, AXONIUS_VPN_DATA_PATH
from axonius.saas.format_ovpn_file import format_ovpn_file
from gui.logic.tunnel_config_builder import DEFAULT_OPENVPN_CONFIG
from services.plugins.openvpn_service import OpenvpnService


def setup_openvpn():
    print(f'Starting the tunneler setup')
    OPENVPN_IMAGE_NAME = 'axonius/openvpn-service'
    try:
        client = docker.from_env()
        # Create the vpnnet network
        client.networks.create(name=TUNNEL_NETWORK,
                               driver='bridge',
                               ipam=docker.types.IPAMConfig(
                                   pool_configs=[docker.types.IPAMPool(subnet=get_tunnel_subnet_ip_rage())]),
                               options={'com.docker.network.bridge.name': DOCKER_TUNNEL_INTERFACE_NAME}
                               )
        # Build the openvpn image
        OpenvpnService().build()

        # Cleanup
        os.makedirs(AXONIUS_VPN_DATA_PATH, exist_ok=True)
        (AXONIUS_VPN_DATA_PATH / 'openvpn.conf').touch()

        # Init OpenVPN and the PKI
        client.containers.run(image=OPENVPN_IMAGE_NAME,
                              volumes={AXONIUS_VPN_DATA_PATH: {'bind': '/etc/openvpn', 'mode': 'rw'}},
                              auto_remove=True,
                              command='ovpn_genconfig -u tcp://server:1194'
                              )
        with open(AXONIUS_VPN_DATA_PATH / 'build-ca.sh', 'w') as fh:
            fh.write(f'echo server | ovpn_initpki nopass')
        os.chmod(AXONIUS_VPN_DATA_PATH / 'build-ca.sh', 0o755)
        client.containers.run(image=OPENVPN_IMAGE_NAME,
                              volumes={AXONIUS_VPN_DATA_PATH: {'bind': '/etc/openvpn', 'mode': 'rw'}},
                              auto_remove=True,
                              command='sh /etc/openvpn/build-ca.sh'
                              )
        with open(AXONIUS_VPN_DATA_PATH / 'openvpn.conf', 'w') as fh:
            fh.write(DEFAULT_OPENVPN_CONFIG)

        # Create customer user
        USERNAME = 'user'
        client.containers.run(image=OPENVPN_IMAGE_NAME,
                              volumes={AXONIUS_VPN_DATA_PATH: {'bind': '/etc/openvpn', 'mode': 'rw'}},
                              auto_remove=True,
                              command=f'easyrsa build-client-full {USERNAME} nopass'
                              )
        client.containers.run(image=OPENVPN_IMAGE_NAME,
                              volumes={AXONIUS_VPN_DATA_PATH: {'bind': '/etc/openvpn', 'mode': 'rw'}},
                              auto_remove=True,
                              command=f'/bin/sh -c "ovpn_getclient {USERNAME} > /etc/openvpn/user_pre.ovpn"'
                              )
        # route everything to that user (non-kernel openvpn routing)
        with open(AXONIUS_VPN_DATA_PATH / 'ccd' / USERNAME, 'w') as fh:
            fh.write('iroute 0.0.0.0 0.0.0.0')
        format_ovpn_file()

    except Exception as err:
        print(f'Error in vpn setup {str(err)}')
    else:
        print(f'Tunneler setup done')
