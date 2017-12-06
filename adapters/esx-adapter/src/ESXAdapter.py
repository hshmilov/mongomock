"""
ESXAdapter.py: An adapter for ESX services.
Currently, allows you to view ESX instances you possess.
"""

__author__ = "Mark Segal"

from vCenterApi import vCenterApi, rawify_vcenter_data
from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
from axonius import AdapterExceptions
from pyVmomi import vim


class ESXAdapter(AdapterBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

    def _get_client_id(self, client_config):
        return '{}/{}'.format(client_config['host'], client_config['user'])

    def _connect_client(self, client_config):
        client_id = self._get_client_id(client_config)
        try:
            return vCenterApi(host=client_config['host'], user=client_config['user'],
                              password=client_config['password'],
                              verify_ssl=client_config['verify_ssl'])
        except vim.fault.InvalidLogin as e:
            message = "Credentials invalid for ESX client for account {0}".format(client_id)
        except vim.fault.HostConnectFault as e:
            message = "Unable to access vCenter, text={}, host = {}".format(
                e.msg, client_config['host'])
        except Exception as e:
            message = "Unknown error on account {}, text={}".format(client_id, str(e))

        self.logger.error(message)
        raise AdapterExceptions.ClientConnectionException(message)

    def _clients_schema(self):
        """
        The schema ESXAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                "host": {
                    "type": "string"
                },
                "user": {
                    "type": "string"
                },
                "password": {
                    "type": "password"
                },
                "verify_ssl": {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "type": "bool"
                }
            },
            "required": [
                "host",
                "user",
                "password",
                "verify_ssl"
            ],
            "type": "object"
        }

    def _query_devices_by_client(self, client_name, client_data):
        return rawify_vcenter_data(client_data.get_all_vms())

    def _parse_raw_data(self, node, _curr_path: str = ""):
        """
        Parses the vms as returned from _query_devices_by_client to the format Aggregator wants

        :param node:
        :param _curr_path: internally used
        :return: iterator(dict)
        """
        if node['Type'] == 'Machine':
            details = node['Details']
            yield {
                "name": node['Name'],
                'OS': figure_out_os(details['config']['guestFullName']),
                'id': details['config']['instanceUuid'],
                'network_interfaces': [self._parse_network_device(x) for x in details.get('networking', [])],
                'hostname': details['guest'].get('hostName'),
                'vmToolsStatus': details['guest'].get('toolsStatus'),
                'physicalPath': _curr_path + "/" + node['Name'],
                'raw': details
            }
        elif node['Type'] in ("Datacenter", "Folder"):
            for child in node['Children']:
                yield from self._parse_raw_data(child, _curr_path + "/" + node['Name'])
        else:
            raise RuntimeError(
                "Found weird type of node: {}".format(node['Type']))

    def _parse_network_device(self, raw_network):
        """
        Parse a network device as received from vCenterAPI
        :param raw_network: device
        :return: dict
        """
        return {
            "MAC": raw_network.get('macAddress'),
            "IP": [addr['ipAddress'] for addr in raw_network.get('ipAddresses', [])],
            # in vCenter/ESX it's not trivial to figure out the 'public IP'
            # the public IP is in the 'simple case' the public IP of the host machine (which we also
            # don't know) but in other cases the host may be connected to multiple network devices
            # itself, all of which aren't necessarily accessible by us, so we leave this blank :)
        }
