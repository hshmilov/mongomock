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
            vms_virtual_nics_async_requests = []
            vms_virtual_nics_devices_objects = []

            for vm_raw in vms_raw:
                try:
                    vm_raw['virtual_nics_data'] = []
                    virtual_nics_ids = list(vm_raw.get("virtualNicIds", []))

                    for virtual_nic_id in virtual_nics_ids:
                        uri = virtual_nic_id.get("uri")
                        if uri is not None:
                            vms_virtual_nics_async_requests.append(
                                {
                                    "name": uri,
                                    "force_full_url": True
                                }
                            )
                            vms_virtual_nics_devices_objects.append(vm_raw)
                except Exception:
                    logger.exception(f"Problem getting vm {vm_raw}")

            # Get info about all nics asynchronously
            for vm_raw, nic_raw in zip(vms_virtual_nics_devices_objects, vms_virtual_nics_async_requests):
                try:
                    if self._is_async_response_good(nic_raw):
                        vm_raw['virtual_nics_data'].append(nic_raw)
                    else:
                        logger.error(f"Problem fetching data of nic, raw answer is {nic_raw} for device {vm_raw}, "
                                     f"not adding nics to device but yielding it")
                except Exception:
                    logger.exception(f"Problem parsing nic async result, result is {nic_raw}, "
                                     f"not adding nics to device")

            yield from vms_raw
        except Exception:
            logger.exception("Problem getting vms")

    def __get_servers(self):
        try:
            servers_raw = self._get('Server')
            servers_ethernet_ports_data_async_requests = []
            servers_ethernet_ports_data_devices = []

            for server_raw in servers_raw:
                # Making sure this is a list
                ethernet_port_ids = list(server_raw.get("ethernetPortIds", []))
                server_raw['ethernet_ports_data'] = []

                for ethernet_port_id in ethernet_port_ids:
                    uri = ethernet_port_id.get("uri")
                    if uri is not None:
                        servers_ethernet_ports_data_async_requests.append(
                            {
                                "name": uri,
                                "force_full_url": True
                            }
                        )
                        servers_ethernet_ports_data_devices.append(server_raw)

                # Now asynchronously get this data
                for server_raw, ethernet_port_raw_answer in \
                        zip(servers_ethernet_ports_data_devices,
                            self._async_get(servers_ethernet_ports_data_async_requests)):
                    try:
                        if self._is_async_response_good(ethernet_port_raw_answer):
                            server_raw['ethernet_ports_data'].append(ethernet_port_raw_answer)
                        else:
                            logger.error(f"problem fetching ethernet of server, data is {ethernet_port_raw_answer} "
                                         f"for server {server_raw}, not adding its ethernet data ")
                    except Exception:
                        logger.exception(f"Exception parsing answer {ethernet_port_raw_answer}, not "
                                         f"adding ethernet ports to server")

            yield from servers_raw
        except Exception:
            logger.exception("Problem getting servers")

    def get_device_list(self):
        yield from [('servers', self.__get_servers()), ('vms', self.__get_vms())]
