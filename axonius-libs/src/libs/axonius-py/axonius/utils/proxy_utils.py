import urllib3

from axonius.consts.plugin_consts import PROXY_ADDR, PROXY_USER, PROXY_PORT, PROXY_PASSW


def to_proxy_string(proxy_data):
    """
    Format proxy paramteres into proxy string format without the protocol prefix
    :param proxy_data: dict with proxy params such as user name, port ip etc
    """
    addr = proxy_data.get(PROXY_ADDR)
    if not proxy_data['enabled'] or not addr:
        return ''

    addr = addr.strip().lower()
    addr = addr.replace('https://', '')
    addr = addr.replace('http://', '')

    ip_port = f'{addr}:{proxy_data[PROXY_PORT]}'
    proxy_string = ip_port
    if proxy_data[PROXY_USER]:
        proxy_string = f'{proxy_data[PROXY_USER]}:{proxy_data[PROXY_PASSW]}@{ip_port}'

    urllib3.ProxyManager(f'https://{proxy_string}')  # test input validity
    return proxy_string
