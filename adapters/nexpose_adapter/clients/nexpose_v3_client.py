import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from axonius.adapter_exceptions import GetDevicesError, ClientConnectionException
from nexpose_adapter.clients.nexpose_base_client import NexposeClient


class NexposeV3Client(NexposeClient):
    def get_all_devices(self):
        devices = []

        try:
            num_of_asset_pages = 1
            current_page_num = -1

            # for current_page_num in range(1, num_of_asset_pages):
            while current_page_num < num_of_asset_pages:
                try:
                    current_page_num += 1
                    current_page_response_as_json = self._send_get_request(
                        'assets', {'page': current_page_num, 'size': self.num_of_simultaneous_devices})
                    devices.extend(current_page_response_as_json.get('resources', []))
                    num_of_asset_pages = current_page_response_as_json.get('page', {}).get('totalPages')
                except Exception:
                    logger.exception(f"Got exception while fetching page {current_page_num+1} "
                                     f"(api page {current_page_num}).")
                    continue

                # num_of_asset_pages might be something that dividing by 100 could lead us to no prints at all like
                # 188 pages.
                if current_page_num % (max(1, round(num_of_asset_pages / 100))) == 0:
                    logger.info(
                        f"Got {current_page_num} out of {num_of_asset_pages} pages. "
                        f"({(current_page_num / max(num_of_asset_pages, 1)) * 100}% of device pages).")

            for item in devices:
                item.update({"API": '3'})
                item.get('osFingerprint', {}).get('cpe', {}).pop('v2.2', None)
                item.get('osFingerprint', {}).get('cpe', {}).pop('v2.3', None)

            return devices
        except Exception as err:
            logger.exception("Error getting the nexpose devices.")
            raise GetDevicesError("Error getting the nexpose devices.")

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
            raise ClientConnectionException(str(e))

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
    def parse_raw_device(device_raw, device_class):
        last_seen = device_raw.get('history', [])[-1].get('date')

        last_seen = super(NexposeV3Client, NexposeV3Client).parse_raw_device_last_seen(last_seen)

        device = device_class()
        device.figure_os(' '.join([device_raw.get('osFingerprint', {}).get('description', ''),
                                   device_raw.get('osFingerprint', {}).get('architecture', '')]))
        device.last_seen = last_seen
        device.id = str(device_raw['id'])
        for address in device_raw.get('addresses', []):
            device.add_nic(address.get('mac'), [address.get('ip')] if 'ip' in address else [])
        device.hostname = device_raw.get('hostName', '')
        risk_score = device_raw.get('riskScore')
        if risk_score is not None:
            try:
                device.risk_score = float(risk_score)
            except Exception:
                logger.exception("Cant get risk score")
        device.set_raw(device_raw)
        return device
