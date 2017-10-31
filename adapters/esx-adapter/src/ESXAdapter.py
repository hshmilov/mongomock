"""
ESXAdapter.py: An adapter for ESX services.
Currently, allows you to view ESX instances you possess.
"""

__author__ = "Mark Segal"

from vCenterApi import vCenterApi, rawify_vcenter_data
from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
from pyVmomi import vim


class ESXAdapter(AdapterBase):
    def __init__(self, *args, **kwargs):
        """
        Check AdapterBase documentation for additional params and exception details.
        """
        super().__init__(*args, **kwargs)

    def _parse_clients_data(self, clients_config):
        clients_dict = {}
        for esx_auth in clients_config:
            name = '{}/{}'.format(esx_auth['host'], esx_auth['user'])
            try:
                clients_dict[name] = vCenterApi(host=esx_auth['host'], user=esx_auth['user'],
                                                password=esx_auth['password'],
                                                verify_ssl=esx_auth['verify_ssl'])
            except vim.fault.InvalidLogin as e:
                self.logger.error("Credentials invalid for ESX client for account {0}".format(name))
            except vim.fault.HostConnectFault as e:
                self.logger.error("Unable to access vCenter, text={}, host = {}".format(e.msg, esx_auth['host']))
            except Exception as e:
                self.logger.error("Unknown error on account {}, text={}".format(name, str(e)))

        return clients_dict

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
                    "type": "string"
                },
                "verify_ssl": { # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
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
            raise RuntimeError("Found weird type of node: {}".format(node['Type']))

    def _parse_network_device(self, raw_network):
        """
        Parse a network device as received from vCenterAPI
        :param raw_network: device
        :return: dict
        """
        return {
            "MAC": raw_network.get('macAddress'),
            "private_ip": [addr['ipAddress'] for addr in raw_network.get('ipAddresses', [])],
            "public_ip": [],  # in vCenter/ESX it's not trivial to figure out the 'public IP'
            # the public IP is in the 'simple case' the public IP of the host machine (which we also
            # don't know) but in other cases the host may be connected to multiple network devices
            # itself, all of which aren't necessarily accessible by us, so we leave this blank :)
        }
