import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from arista_eos_adapter.consts import AristaEOSCommads, COMMAND_API, ARP_INFO, BASIC_INFO
logger = logging.getLogger(f'axonius.{__name__}')


class AristaEosConnection(RESTConnection):
    """ rest client for AristaEos adapter """

    def __init__(self, *args, enable=None, **kwargs):
        super().__init__(*args,
                         headers={'Content-Type': 'application/json-rpc', 'Accept': 'application/json-rpc'},
                         **kwargs)
        self._enable_pwd = enable

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        json_rpc = self._eos_json_rpc_request(AristaEOSCommads.enable, AristaEOSCommads.show_version)
        response = self._post('command-api', body_params=json_rpc, do_basic_auth=True)
        if 'error' in response and 'message' in response['error']:
            raise RESTException('error found in command-api response')

    def _eos_json_rpc_request(self, *cmds) -> dict:
        commands = []
        if self._enable_pwd:
            commands.append({'cmd': 'enable', 'input': self._enable_pwd})
        else:
            commands.append('enable')

        for cmd in cmds:
            if isinstance(cmd,  AristaEOSCommads):
                commands.append(cmd.value)
            else:
                raise RuntimeError('request command must be type of AristaEOSCommads enum')

        json_rpc = {'jsonrpc': '2.0',
                    'method': 'runCmds',
                    'params': {
                        'version': 1,
                        'cmds': commands,
                        'format': 'json'
                    },
                    'id': id(self)}
        return json_rpc

    # pylint: disable=pointless-string-statement
    def _eapi_cmd_handler(self, *cmds: list) -> dict:
        try:

            json_rpc = self._eos_json_rpc_request(*cmds)
            response = self._post(COMMAND_API, body_params=json_rpc, do_basic_auth=True)

            '''
            Notice :eAPI Respose Result first item resever for messages , data start from item 1.
            '''

            if 'result' in response and isinstance(response['result'][1], dict):
                return response['result']

            if 'error' in response and 'message' in response['error']:
                logger.error(response['error']['message'])
            else:
                logger.error(f'unkown resposne received for cmds {cmds} ')

            return None

        except Exception:
            logger.exception(f'Exception on command {cmds}')
            return None

    def _get_arp_info(self):
        response = self._eapi_cmd_handler(AristaEOSCommads.show_arp)

        if response is None:
            logger.error(f'Unexpected empty response for -- >  {AristaEOSCommads.show_arp}')
            return

        for response_entery in response:
            if isinstance(response_entery, dict) and 'ipV4Neighbors' in response_entery:
                for arp_entry in response_entery['ipV4Neighbors']:
                    try:
                        yield {ARP_INFO: arp_entry}
                    except Exception:
                        logger.exception(f'fatal error with ARP Entry {arp_entry} ')

    def _get_basic_info(self):
        response = self._eapi_cmd_handler(AristaEOSCommads.show_version,
                                          AristaEOSCommads.show_hostname,
                                          AristaEOSCommads.show_interfaces)

        if response and len(response) > 2 \
                and isinstance(response[1], dict)\
                and isinstance(response[2], dict)\
                and isinstance(response[3], dict):

            yield {BASIC_INFO: {**response[1], **response[2], **response[3]}}

        else:
            logger.error(f'unknown response for basic info {response}')

    def get_device_list(self):
        """
        Arista eAPI JSON-RPC doesn't support PAGE/LIMIT params
        """
        try:
            yield from self._get_basic_info()
        except Exception:
            logger.exception('failed get fettch basic info ')

        try:
            yield from self._get_arp_info()
        except Exception:
            logger.exception('failed get fetch aro info ')
