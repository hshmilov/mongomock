"""
ESXAdapter.py: An adapter for ESX services.
Currently, allows you to view ESX instances you possess.
"""

__author__ = "Mark Segal"

from vcenter_api import vCenterApi, rawify_vcenter_data
from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import figure_out_os
from axonius import adapter_exceptions
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
        raise adapter_exceptions.ClientConnectionException(message)

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
        if node.get('Type', '') == 'Machine':
            details = node.get('Details', {})
            yield {
                "name": node.get('Name', ''),
                'OS': figure_out_os(details.get('config', {}).get('guestFullName', '')),
                'id': details.get('config', {})['instanceUuid'],
                'network_interfaces': self._parse_network_device(details.get('networking', [])),
                'hostname': details.get('guest', {}).get('hostName', ''),
                'vmToolsStatus': details.get('guest', {}).get('toolsStatus', ''),
                'physicalPath': _curr_path + "/" + node.get('Name', ''),
                'raw': details
            }
        elif node.get('Type', '') in ("Datacenter", "Folder", "Root"):
            for child in node.get('Children', [{}]):
                yield from self._parse_raw_data(child, _curr_path + "/" + node['Name'])
        else:
            raise RuntimeError(
                "Found weird type of node: {}".format(node['Type']))

    def _parse_network_device(self, raw_networks):
        """
        Parse a network device as received from vCenterAPI
        :param raw_network: raw networks from ESX
        :return: iter(dict)
        """
        for raw_network in raw_networks:
            ip_to_return = [addr['ipAddress'] for addr in raw_network.get('ipAddresses', [])]
            if len(ip_to_return) == 0:
                continue
            # Return only if has an IP address
            yield {
                "MAC": raw_network.get('macAddress', ''),
                "IP": ip_to_return
            }
