"""
sccm_adapter.py: An adapter for Sccm Dashboard.
"""

from axonius.device import Device
import axonius.adapter_exceptions
from axonius.adapter_base import AdapterBase
from axonius.adapter_base import adapter_consts
import sccm_connection
import sccm_exceptions
import sccm_consts
import configparser


class SccmAdapter(AdapterBase):

    class MyDevice(Device):
        pass

    def __init__(self, **kwargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """

        # Getting needed paths for execution
        config = configparser.ConfigParser()
        config.read('plugin_config.ini')
        self.alive_hours = config['DEFAULT'][adapter_consts.DEFAULT_DEVICE_ALIVE_THRESHOLD_HOURS]
        self.devices_fetched_at_a_time = int(config['DEFAULT'][sccm_consts.DEVICES_FETECHED_AT_A_TIME])
        super().__init__(**kwargs)

    def _get_client_id(self, client_config):
        return client_config[sccm_consts.SCCM_HOST]

    def _connect_client(self, client_config):
        try:
            connection = sccm_connection.SccmConnection(logger=self.logger,
                                                        database=client_config[sccm_consts.SCCM_DATABASE],
                                                        server=client_config[sccm_consts.SCCM_HOST],
                                                        port=client_config[sccm_consts.SCCM_PORT],
                                                        devices_paging=self.devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[sccm_consts.USER],
                                       password=client_config[sccm_consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except sccm_exceptions.SccmException:
            message = f"Error connecting to client with parameters {str(client_config)} "
            self.logger.exception(message)
            raise axonius.adapter_exceptions.ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Sccm domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Sccm connection

        :return: A json with all the attributes returned from the Sccm Server
        """
        with client_data:
            return list(client_data.query(sccm_consts.SCCM_QUERY.format(self.alive_hours)))

    def _clients_schema(self):
        """
        The schema SccmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": sccm_consts.SCCM_HOST,
                    "title": "SCCM/MSSQL Server",
                    "type": "string"
                },
                {
                    "name": sccm_consts.SCCM_PORT,
                    "title": "Port",
                    "type": "integer"
                },
                {
                    "name": sccm_consts.SCCM_DATABASE,
                    "title": "Database",
                    "type": "string"
                },
                {
                    "name": sccm_consts.USER,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": sccm_consts.PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                sccm_consts.SCCM_HOST,
                sccm_consts.USER,
                sccm_consts.PASSWORD,
                sccm_consts.SCCM_DATABASE
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:

            device = self._new_device()
            device.id = device_raw.get('Distinguished_Name0')
            device.hostname = (device_raw.get('Netbios_Name0') or '') + '.' + \
                (device_raw.get('Full_Domain_Name0') or '')
            device.figure_os((device_raw.get('Caption0') or '') + (device_raw.get("Operating_System_Name_and0") or ''))
            for nic in (device_raw.get('Network Interfaces') or '').split(';'):
                mac, ips = nic.split('@')
                device.add_nic(mac, ips.split(', '))
            device.last_seen = device_raw.get('Last Seen')
            device.set_raw(device_raw)
            yield device

    def _correlation_cmds(self):
        """
        Correlation commands for Sccm
        :return: shell commands that help correlations
        """
        self.logger.error("correlation_cmds is not implemented for sccm adapter")
        raise NotImplementedError("correlation_cmds is not implemented for sccm adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        self.logger.error("_parse_correlation_results is not implemented for sccm adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for sccm adapter")
