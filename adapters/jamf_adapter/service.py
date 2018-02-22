from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device import Device
from axonius.utils.files import get_local_config_file
from jamf_adapter import consts
from jamf_adapter.connection import JamfConnection
from jamf_adapter.exceptions import JamfException


class JamfAdapter(AdapterBase):

    class MyDevice(Device):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['Jamf_Domain']

    def _connect_client(self, client_config):
        try:
            connection = JamfConnection(logger=self.logger,
                                        domain=client_config[consts.JAMF_DOMAIN],
                                        http_proxy=client_config.get(consts.HTTP_PROXY),
                                        https_proxy=client_config.get(consts.HTTPS_PROXY))
            connection.set_credentials(username=client_config[consts.USERNAME],
                                       password=client_config[consts.PASSWORD])
            connection.connect()
            return connection
        except JamfException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Jamf_Domain'], str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Jamf domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Jamf connection

        :return: A json with all the attributes returned from the Jamf Server
        """
        return client_data.get_devices()

    def _clients_schema(self):
        """
        The schema JamfAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": consts.JAMF_DOMAIN,
                    "title": "Jamf Domain",
                    "type": "string"
                },
                {
                    "name": consts.USERNAME,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": consts.PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": consts.HTTP_PROXY,
                    "title": "Http Proxy",
                    "type": "string"
                },
                {
                    "name": consts.HTTPS_PROXY,
                    "title": "Https Proxy",
                    "type": "string"
                }
            ],
            "required": [
                consts.JAMF_DOMAIN,
                consts.USERNAME,
                consts.PASSWORD
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._new_device()
            device.hostname = device_raw.get('name', '')
            device.id = device_raw.get('udid', '')
            if 'Operating_System' in device_raw:
                # The field 'Operating_System' means that we are handling a computer, and not a mobile.
                # Thus we believe the following fields will be present.
                device.figure_os(' '.join([device_raw.get('Operating_System', ''),
                                           device_raw.get('Architecture_Type', '')]))
                device.add_nic(device_raw.get('MAC_Address', ''), [device_raw.get('IP_Address', '')], self.logger)

                for app in device_raw.get('Applications', {}).get('Application', []):
                    device.add_installed_software(
                        name=app.get('Application_Title', ''),
                        version=app.get('Application_Version', '')
                    )
                total_ram_mb = device_raw.get('Total_RAM_MB')
                if total_ram_mb is not None:
                    total_ram_mb = float(total_ram_mb)
                    device.total_physical_memory = total_ram_mb / 1024.0

                total_number_of_physical_procesors = device_raw.get("Number_of_Processors")
                if total_number_of_physical_procesors is not None:
                    device.total_number_of_physical_processors = int(total_number_of_physical_procesors)

                total_number_of_cores = device_raw.get("Total_Number_of_Cores")
                if total_number_of_cores is not None:
                    device.total_number_of_cores = int(total_number_of_cores)
                processor_speed_mhz = device_raw.get("Processor_Speed_MHz")
                processor_type = device_raw.get("Processor_Type")
                boot_drive_available = device_raw.get("Boot_Drive_Available_MB")
                boot_drive_full_percentage = device_raw.get("Boot_Drive_Percentage_Full")
                if boot_drive_available is not None and boot_drive_full_percentage is not None:
                    device.add_hd(total_size=100.0 * float(boot_drive_available) /
                                  (100.0 - float(boot_drive_full_percentage)) / 1024,
                                  free_size=float(boot_drive_available) / 1024)
                if processor_speed_mhz is not None and processor_type is not None:
                    device.add_cpu(
                        name=processor_type,
                        ghz=float(processor_speed_mhz) / 1024.0
                    )
                device.device_manufacturer = device_raw.get('Make')
            else:
                device.figure_os(' '.join([device_raw.get('Model_Identifier', ''), device_raw.get('iOS_Version', '')]))
                device.add_nic(device_raw.get('Wi_Fi_MAC_Address', ''), [device_raw.get('IP_Address', '')], self.logger)

            device.device_model = device_raw.get('Model_Identifier')
            device.device_model_family = device_raw.get('Model')
            device.device_serial = device_raw.get("Serial_Number")
            device.set_raw(device_raw)
            yield device

    def _correlation_cmds(self):
        """
        Correlation commands for Jamf
        :return: shell commands that help correlations
        """

        self.logger.error("correlation_cmds is not implemented for jamf adapter")
        raise NotImplementedError("correlation_cmds is not implemented for jamf adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        self.logger.error("_parse_correlation_results is not implemented for jamf adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for jamf adapter")
