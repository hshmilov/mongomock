import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from oracle_vm_adapter.consts import SERVERS_KEY_WORD, VMS_KEY_WORD

logger = logging.getLogger(f'axonius.{__name__}')


class OracleVmConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='ovm/core/wsapi/rest/',
                         headers={'Content-Type': 'application/json-rpc', 'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No user name or password')

        response = self._get('Manager', do_basic_auth=True)
        if not response or not isinstance(response, list) or not isinstance(response[0], dict) or \
                not response[0].get('managerRunState') or response[0].get('managerRunState').upper() != 'RUNNING':
            raise RESTException(f'Server not in Running mode. Response was {response}')

    def __get_vms(self):
        try:
            vms_raw = self._get('Vm')
            vms_virtual_nics_async_requests = []
            vms_virtual_nics_devices_objects = []

            for vm_raw in vms_raw:
                try:
                    vm_raw['virtual_nics_data'] = []
                    virtual_nics_ids = vm_raw.get('virtualNicIds')
                    if not isinstance(virtual_nics_ids, list):
                        virtual_nics_ids = []

                    for virtual_nic_id in virtual_nics_ids:
                        uri = virtual_nic_id.get('uri')
                        if uri is not None:
                            vms_virtual_nics_async_requests.append(
                                {
                                    'name': uri,
                                    'force_full_url': True,
                                    'do_basic_auth': True
                                }
                            )
                            vms_virtual_nics_devices_objects.append(vm_raw)
                except Exception:
                    logger.exception(f'Problem getting vm {vm_raw}')

            # Get info about all nics asynchronously
            for vm_raw, nic_raw in zip(vms_virtual_nics_devices_objects,
                                       self._async_get(vms_virtual_nics_async_requests)):
                try:
                    if self._is_async_response_good(nic_raw):
                        vm_raw['virtual_nics_data'].append(nic_raw)
                    else:
                        logger.error(f'Problem fetching data of nic, raw answer is {nic_raw} for device {vm_raw}, '
                                     f'not adding nics to device but yielding it')
                except Exception:
                    logger.exception(f'Problem parsing nic async result, result is {nic_raw}, '
                                     f'not adding nics to device')

            yield from vms_raw
        except Exception:
            logger.exception('Problem getting vms')

    def __get_servers(self):
        try:
            servers_raw = self._get('Server')
            servers_ethernet_ports_data_async_requests = []
            servers_ethernet_ports_data_devices = []

            for server_raw in servers_raw:
                # Making sure this is a list
                ethernet_port_ids = server_raw.get('ethernetPortIds')
                if not isinstance(ethernet_port_ids, list):
                    ethernet_port_ids = []
                server_raw['ethernet_ports_data'] = []

                for ethernet_port_id in ethernet_port_ids:
                    uri = ethernet_port_id.get('uri')
                    if uri is not None:
                        servers_ethernet_ports_data_async_requests.append(
                            {
                                'name': uri,
                                'force_full_url': True,
                                'do_basic_auth': True
                            }
                        )
                        servers_ethernet_ports_data_devices.append(server_raw)

                # Now asynchronously get this data
                for server_raw, ethernet_port_raw_answer in zip(servers_ethernet_ports_data_devices,
                                                                self._async_get(servers_ethernet_ports_data_async_requests)):
                    try:
                        if self._is_async_response_good(ethernet_port_raw_answer):
                            server_raw['ethernet_ports_data'].append(ethernet_port_raw_answer)
                        else:
                            logger.error(f'problem fetching ethernet of server, data is {ethernet_port_raw_answer} '
                                         f'for server {server_raw}, not adding its ethernet data ')
                    except Exception:
                        logger.exception(f'Exception parsing answer {ethernet_port_raw_answer}, not '
                                         f'adding ethernet ports to server')

            yield from servers_raw
        except Exception:
            logger.exception('Problem getting servers')

    def get_device_list(self):
        for device_raw in self.__get_servers():
            yield SERVERS_KEY_WORD, device_raw
        for device_raw in self.__get_vms():
            yield VMS_KEY_WORD, device_raw
