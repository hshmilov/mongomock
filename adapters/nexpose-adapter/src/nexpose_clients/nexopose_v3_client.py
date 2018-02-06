import dateutil.parser
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from nexpose_clients import nexpose_base_client
import axonius.adapter_exceptions


class NexposeV3Client(nexpose_base_client.NexposeClient):
    def get_all_devices(self):
        devices = []

        try:
            num_of_asset_pages = 1
            current_page_num = 0

            # for current_page_num in range(1, num_of_asset_pages):
            while current_page_num < num_of_asset_pages:
                current_page_response_as_json = self._send_get_request(
                    'assets', {'page': current_page_num, 'size': self.num_of_simultaneous_devices})
                devices.extend(current_page_response_as_json.get('resources', []))
                num_of_asset_pages = current_page_response_as_json.get('page', {}).get('totalPages')

                if (current_page_num + 1) % (num_of_asset_pages / 10) == 0:
                    self.logger.info(
                        f"Got {(((current_page_num + 1) / (num_of_asset_pages / 10)) * 10)}% of device pages.")
                current_page_num += 1

            for item in devices:
                item.update({"API": '3'})
                item.get('osFingerprint', {}).get('cpe', {}).pop('v2.2', None)
                item.get('osFingerprint', {}).get('cpe', {}).pop('v2.3', None)

            return devices
        except Exception as err:
            self.logger.exception("Error getting the nexpose devices.")
            raise axonius.adapter_exceptions.GetDevicesError("Error getting the nexpose devices.")

    def _send_get_request(self, resource, params=None):
        """
        Sends a get request to the client (authenticated, and ssl_verified configured).
        :param resource: The restful resource to get.
        :param params: The params of the get request.
        :return: The response of the get request.
        """
        def _parse_dedicated_url(resource):
            return f'https://{self.host}:{self.port}/api/3/{resource}'

        try:
            response = requests.get(_parse_dedicated_url(resource), params=params,
                                    auth=(self.username, self.password), verify=self.verify_ssl)
            response.raise_for_status()
            response = response.json()
        except requests.HTTPError as e:
            raise axonius.adapter_exceptions.ClientConnectionException(str(e))

        return response

    def _does_api_exist(self):
        """ Sends a get request to the api root to see if the api version exists.

        :param client_config: The configure of the client to test.
        :return: bool that signifies if this api version exists on the client.
        """
        self._send_get_request('')

        # The get request would have raised exception if status_code wasn't 200 on response.raise_for_status().
        return True

    @staticmethod
    def parse_raw_device(device_raw, device_class, logger):
        last_seen = device_raw.get('history', [])[-1].get('date')

        last_seen = super(NexposeV3Client, NexposeV3Client).parse_raw_device_last_seen(last_seen)

        device = device_class()
        device.figure_os(' '.join([device_raw.get('osFingerprint', {}).get('description', ''),
                                   device_raw.get('osFingerprint', {}).get('architecture', '')]))
        device.last_seen = last_seen
        device.id = str(device_raw['id'])
        for address in device_raw.get('addresses', []):
            device.add_nic(address.get('mac'), [address.get('ip')] if 'ip' in address else [], logger)
        device.hostname = device_raw.get('hostName', '')
        device.scanner = True
        device.set_raw(device_raw)
        return device
