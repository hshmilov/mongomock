import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException


class OracleVmConnection(RESTConnection):
    def _connect(self):
        if self._username is not None and self._password is not None:
            response = self._get('Manager', do_basic_auth=True)
            if response.get("managerRunState", "").upper() != 'RUNNING':
                raise RESTException(f"Server not in Running mode. Response was {response}")
        else:
            raise RESTException("No user name or password")

    def __get_vms(self):
        try:
            vms_raw = self._get('Vm')
            for vm_raw in vms_raw:
                try:
                    virtual_nics_ids = list(vm_raw.get("virtualNicIds", []))
                    virtual_nics_data = []
                    for virtual_nic_id in virtual_nics_ids:
                        try:
                            virtual_nics_data.append(self._get(virtual_nic_id.get("uri"), force_full_url=True))
                        except Exception:
                            logger.exception(f"Problem getting virtual nic for vm {vm_raw}")
                    vm_raw['virtual_nics_data'] = virtual_nics_data
                    yield vm_raw
                except Exception:
                    logger.exception(f"Problem getting vm {vm_raw}")
        except Exception:
            logger.exception("Problem getting vms")

    def __get_servers(self):
        try:
            servers_raw = self._get('Server')
            for server_raw in servers_raw:
                # Making sure this is a list
                ethernet_port_ids = list(server_raw.get("ethernetPortIds", []))
                etherent_ports_data = []
                for ethernet_port_id in ethernet_port_ids:
                    try:
                        etherent_ports_data.append(self._get(ethernet_port_id.get("uri"), force_full_url=True))
                    except Exception:
                        logger.exception(f"Problem getting ethernet port for server {server_raw}")
                server_raw['ethernet_ports_data'] = etherent_ports_data
                yield server_raw
        except Exception:
            logger.exception("Problem getting servers")

    def get_device_list(self):
        yield from [('servers', self.__get_servers()), ('vms', self.__get_vms())]
