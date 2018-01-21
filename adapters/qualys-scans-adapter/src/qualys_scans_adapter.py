"""
QualysScansAdapter.py: An adapter for Qualys Scans Dashboard.
"""

__author__ = "Asaf & Tal"

import dateutil.parser

import axonius.adapter_exceptions
from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import figure_out_os
import qualys_scans_connection
import qualys_scans_exceptions
from axonius.consts import adapter_consts
from axonius.utils.xml2json_parser import Xml2Json
from axonius.consts.adapter_consts import SCANNER_FIELD

QUALYS_SCANS_ITERATOR_FORMAT = """
<?xml version="1.0" encoding="UTF-8" ?>
<ServiceRequest>
 <preferences>
 <startFromId>{0}</startFromId>
 <limitResults>{1}</limitResults>
 </preferences>
</ServiceRequest>
"""

QUALYS_SCANS_DOMAIN = 'Qualys_Scans_Domain'
USERNAME = 'username'
PASSWORD = 'password'

ALL_HOSTS_URL = "asset/host/"
ALL_HOSTS_PARAMS = 'action=list&details=All&truncation_limit=1000&id_min=0&show_tags=1'
ALL_HOSTS_OUTPUT = 'HOST_LIST_OUTPUT'

VM_HOST_URL = "asset/host/vm/detection/"
VM_HOST_PARAMS = 'action=list&truncation_limit=1000&id_min=0&show_tags=1'
VM_HOST_OUTPUT = 'HOST_LIST_VM_DETECTION_OUTPUT'


class QualysScansAdapter(AdapterBase):

    def _get_client_id(self, client_config):
        return client_config[QUALYS_SCANS_DOMAIN]

    def _connect_client(self, client_config):
        try:
            connection = qualys_scans_connection.QualysScansConnection(logger=self.logger,
                                                                       domain=client_config[QUALYS_SCANS_DOMAIN])
            connection.set_credentials(username=client_config[USERNAME], password=client_config[PASSWORD])
            with connection:
                pass
            return connection
        except qualys_scans_exceptions.QualysScansException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config[QUALYS_SCANS_DOMAIN], str(e))
            self.logger.exception(message)
            raise axonius.adapter_exceptions.ClientConnectionException(message)

    def _get_qualys_scan_results(self, client_data, url, params, output_key):
        with client_data:
            client_list = []
            while params:
                response = client_data.get(url + '?' + params, auth=client_data.auth, headers=client_data.headers)
                current_clients_page = Xml2Json(response.text).result
                try:
                    # if there's no response field - there are no clients
                    response_json = current_clients_page[output_key]['RESPONSE']
                    client_list.extend(response_json.get('HOST_LIST', {}).get('HOST'))
                except KeyError:
                    self.logger.warn(f"No devices found: {response.text}")
                    return client_list
                params = response_json.get('WARNING', {}).get('URL', "?").split("?")[1]
            return client_list

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific QualysScans domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a QualysScans connection

        :return: A json with all the attributes returned from the QualysScans Server
        """

        all_hosts = {device['ID']: device for device in self._get_qualys_scan_results(client_data, url=ALL_HOSTS_URL,
                                                                                      params=ALL_HOSTS_PARAMS,
                                                                                      output_key=ALL_HOSTS_OUTPUT)}
        vm_hosts = self._get_qualys_scan_results(client_data, url=VM_HOST_URL,
                                                 params=VM_HOST_PARAMS, output_key=VM_HOST_OUTPUT)

        for device in vm_hosts:
            all_hosts[device['ID']]['DETECTION_LIST'] = device.get('DETECTION_LIST', {})
        return all_hosts.values()

    def _clients_schema(self):
        """
        The schema QualysScansAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                QUALYS_SCANS_DOMAIN: {
                    "type": "string",
                    "name": "QualysScans Domain"
                },
                USERNAME: {
                    "type": "string",
                    "name": USERNAME
                },
                PASSWORD: {
                    "type": "password",
                    "name": PASSWORD
                }
            },
            "required": [
                QUALYS_SCANS_DOMAIN,
                USERNAME,
                PASSWORD
            ],
            "type": "object"
        }

    def _parse_raw_data(self, raw_devices):
        no_timestamp_count = 0
        no_hostname_count = 0
        for raw_device_data in raw_devices:
            hostname = raw_device_data.get('DNS', raw_device_data.get('NETBIOS', ''))
            if hostname == '':
                no_hostname_count += 1
                continue
            else:
                try:
                    last_seen = raw_device_data.get('LAST_VM_SCANNED_DATE',
                                                    raw_device_data.get('LAST_VULN_SCAN_DATETIME'))
                    if last_seen is None:
                        # No data on the last timestamp of the device. Not inserting this device.
                        no_timestamp_count += 1
                        continue

                    # Parsing the timestamp.
                    last_seen = dateutil.parser.parse(last_seen)
                except Exception:
                    self.logger.exception("An Exception was raised while getting and parsing the last_seen field.")

                yield {
                    'hostname': hostname,
                    'OS': figure_out_os(raw_device_data.get('OS', '')),
                    adapter_consts.LAST_SEEN_PARSED_FIELD: last_seen,
                    'network_interfaces': [{'IP': [raw_device_data.get('IP', '')],
                                            'MAC': ''}],
                    'id': raw_device_data.get('ID'),
                    SCANNER_FIELD: True,
                    'raw': raw_device_data
                }

        if no_timestamp_count != 0:
            self.logger.warning(f"Got {no_timestamp_count} with no timestamp while parsing data")

        if no_hostname_count != 0:
            self.logger.warning(f"Got {no_hostname_count} with no hostname while parsing data")

    def _correlation_cmds(self):
        """
        Correlation commands for QualysScans
        :return: shell commands that help correlations
        """

        self.logger.error("correlation_cmds is not implemented for qualys adapter")
        raise NotImplementedError("correlation_cmds is not implemented for qualys adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        self.logger.error("_parse_correlation_results is not implemented for qualys adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for qualys adapter")
