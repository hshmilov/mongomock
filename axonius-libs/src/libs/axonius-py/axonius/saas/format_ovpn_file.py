#!/usr/bin/env python3
# Should be imported from inside the docker and outside the docker
from axonius.saas.input_params import read_saas_input_params
from scripts.instances.instances_consts import VPN_DATA_DIR

import netifaces

CLIENT_FILE_PATH = VPN_DATA_DIR / 'user_pre.ovpn'

OVPN_FILE_TEMPLATE = '''

client
nobind
dev tun
remote-cert-tls server
proto tcp
remote {SERVER_ADDR} {PORT} tcp

{KEYS}

'''


def calc_openvpn_address():
    # this is somewhat complicated issue. Not always one can compute
    # the 'public addr'. For now just gives machine's main ip addr
    my_gateways = netifaces.gateways()
    my_default = my_gateways['default']
    af_inet = my_default[netifaces.AF_INET]
    iface_name = af_inet[1]
    # return the first AF_INET addr of the interdace that is our default
    return netifaces.ifaddresses(iface_name)[netifaces.AF_INET][0]['addr']


def format_ovpn_file():
    if not CLIENT_FILE_PATH.is_file():
        print(f'Client file is not present')

    keys_section = CLIENT_FILE_PATH.read_text()
    keys_section = keys_section.replace('redirect-gateway def1', '')
    keys_section = keys_section.split('remote server 1194 tcp')[1]
    try:
        saas_params = read_saas_input_params()
    except Exception:
        print('Couldn\'t get params from SaaS instance')
        server_addr = calc_openvpn_address()
        port = 2212
    else:
        server_addr = saas_params['TUNNEL_URL'] if saas_params and 'TUNNEL_URL' in saas_params \
            else calc_openvpn_address()
        port = 443 if saas_params and 'TUNNEL_URL' in saas_params else 2212

    formatted_file = OVPN_FILE_TEMPLATE.format(SERVER_ADDR=server_addr, KEYS=keys_section, PORT=port)
    (VPN_DATA_DIR / 'user.ovpn').write_text(formatted_file)


if __name__ == '__main__':
    format_ovpn_file()
