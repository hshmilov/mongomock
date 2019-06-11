import logging
import math
import urllib3

import aiohttp
import requests

from axonius.adapter_exceptions import GetDevicesError, ClientConnectionException
from nexpose_adapter.clients.nexpose_base_client import NexposeClient
from axonius.utils.parsing import figure_out_cloud
from axonius.async.utils import async_request
from axonius.utils.json import from_json


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(f'axonius.{__name__}')
MAX_ASYNC_REQUESTS_IN_PARALLEL = 100


class NexposeV3Client(NexposeClient):

    def _get_async_data(self, devices, data_type):
        # Get all tags for all devices asynchronously
        # Build the requests
        aio_requests = []
        aio_ids = []
        for i, item in enumerate(devices):
            item_id = item.get('id')
            if not item_id:
                logger.warning("Got device with no id, not yielding")
                continue

            aio_req = dict()
            aio_req['method'] = "GET"
            aio_req['url'] = f'https://{self.host}:{self.port}/api/3/assets/{item_id}/{data_type}'
            aio_req['auth'] = (self.username, self.password)
            aio_req['timeout'] = (5, 30)

            if self.verify_ssl is False:
                aio_req['ssl'] = False
            aio_requests.append(aio_req)
            aio_ids.append(i)

        for chunk_id in range(int(math.ceil(len(aio_requests) / MAX_ASYNC_REQUESTS_IN_PARALLEL))):
            logger.debug(
                f"Async requests: sending {chunk_id * MAX_ASYNC_REQUESTS_IN_PARALLEL} out of {len(aio_requests)}")

            all_answers = async_request(
                aio_requests[MAX_ASYNC_REQUESTS_IN_PARALLEL * chunk_id:
                             MAX_ASYNC_REQUESTS_IN_PARALLEL * (chunk_id + 1)])

            # We got the requests,
            # time to check if they are valid and transform them to what the user wanted.

            for i, raw_answer in enumerate(all_answers):
                request_id_absolute = MAX_ASYNC_REQUESTS_IN_PARALLEL * chunk_id + i
                current_device = devices[aio_ids[request_id_absolute]]
                try:
                    # The answer could be an exception
                    if isinstance(raw_answer, Exception):
                        logger.debug(f"Exception getting tags for request {request_id_absolute}, yielding"
                                     f" device with no tags. Data type {data_type}. Exception {raw_answer}")

                    # Or, it can be the actual response
                    elif isinstance(raw_answer, tuple) and isinstance(raw_answer[0], str) \
                            and isinstance(raw_answer[1], aiohttp.ClientResponse):
                        text_answer = raw_answer[0]
                        response_object = raw_answer[1]

                        try:
                            response_object.raise_for_status()
                            current_device[data_type] = from_json(text_answer)['resources']
                        except aiohttp.ClientResponseError as e:
                            logger.debug(f"async error code {e.status} on "
                                         f"request id {request_id_absolute}. "
                                         f"original response is {raw_answer}. Yielding with no tags")
                        except Exception:
                            logger.debug(f"Exception while parsing async response for {text_answer}"
                                         f". Yielding with no tags")
                    else:
                        msg = f"Got an async response which is not exception or ClientResponse. " \
                              f"This should never happen! response is {raw_answer}"
                        logger.critical(msg)
                except Exception:
                    msg = f"Error while parsing request {request_id_absolute} - {raw_answer}, continuing"
                    logger.exception(msg)

    def get_all_devices(self, fetch_tags=False):
        logger.info(f'Stating to fetch devices on V3 for nexpose')
        try:
            num_of_asset_pages = 1
            current_page_num = -1

            # for current_page_num in range(1, num_of_asset_pages):
            while current_page_num < num_of_asset_pages:
                try:
                    current_page_num += 1
                    current_page_response_as_json = self._send_get_request(
                        'assets', {'page': current_page_num, 'size': self.num_of_simultaneous_devices})
                    devices = current_page_response_as_json.get('resources', [])
                    num_of_asset_pages = current_page_response_as_json.get('page', {}).get('totalPages')
                    for item in devices:
                        item.update({"API": '3'})

                    if fetch_tags:
                        self._get_async_data(devices, 'tags')
                        self._get_async_data(devices, 'software')
                    yield from devices

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
                                    auth=(self.username, self.password), verify=self.verify_ssl,
                                    timeout=(5, 300))
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
        logger.info(f'Checking API for nexpose V3')
        self._send_get_request('')

        # The get request would have raised exception if status_code wasn't 200 on response.raise_for_status().
        return True

    @staticmethod
    def parse_raw_device(device_raw, device_class, drop_only_ip_devices=False):
        last_seen = device_raw.get('history', [])[-1].get('date')

        last_seen = super(NexposeV3Client, NexposeV3Client).parse_raw_device_last_seen(last_seen)

        device = device_class()
        device.figure_os(' '.join([device_raw.get('osFingerprint', {}).get('description', ''),
                                   device_raw.get('osFingerprint', {}).get('architecture', '')]))
        device.last_seen = last_seen
        device.id = str(device_raw['id']) + (device_raw.get('hostName') or '')
        got_mac = False
        for address in device_raw.get('addresses', []):
            if address.get('mac'):
                got_mac = True
            device.add_nic(address.get('mac'), [address.get('ip')] if ('ip' in address and
                                                                       isinstance(address.get('ip'), str) and
                                                                       address.get('ip') != '0.0.0.0') else [])
        if not device_raw.get('hostName') and not got_mac and drop_only_ip_devices:
            return None
        device.hostname = device_raw.get('hostName', '')
        risk_score = device_raw.get('riskScore')
        if risk_score is not None:
            try:
                device.risk_score = float(risk_score)
            except Exception:
                logger.exception("Cant get risk score")
        try:
            vulnerabilities_raw = device_raw.get("vulnerabilities", {})
            device.vulnerabilities_critical = vulnerabilities_raw.get("critical")
            device.vulnerabilities_exploits = vulnerabilities_raw.get("exploits")
            device.vulnerabilities_malwareKits = vulnerabilities_raw.get("malwareKits")
            device.vulnerabilities_moderate = vulnerabilities_raw.get("moderate")
            device.vulnerabilities_severe = vulnerabilities_raw.get("severe")
            device.vulnerabilities_total = vulnerabilities_raw.get("total")
        except Exception:
            logger.exception(f"Problem getting vulns for {device_raw}")

        try:
            for id_element in device_raw.get('ids', []):
                cloud_type = figure_out_cloud(id_element.get("source"))
                if cloud_type is not None:
                    device.cloud_provider = cloud_type
                    device.cloud_id = id_element.get("id")
                    break

        except Exception:
            logger.exception(f"Error getting id's array from Rapid7 Nexpose: {device_raw.get('ids')}")

        try:
            software = device_raw.get('software') or []
            if software and isinstance(software, list):
                for software_data in software:
                    try:
                        sw_name = software_data.get('product')
                        sw_version = software_data.get('version')
                        sw_vendor = software_data.get('vendor')
                        if not sw_name:
                            logger.warning(f'Bad software at device {device_raw}')
                            continue
                        device.add_installed_software(name=sw_name,
                                                      vendor=sw_vendor,
                                                      version=sw_version)
                    except Exception:
                        logger.exception(f'Problem adding tag {software_data}')
        except Exception:
            logger.exception(f'Problem parsing sw')

        try:
            tags = device_raw.get('tags') or []
            if tags and isinstance(tags, list):
                for tag in tags:
                    try:
                        tag_type = tag.get('type')
                        tag_name = tag.get('name')
                        if not tag_type:
                            logger.warning(f'Bad tag type at device {device_raw}')
                            continue
                        if tag_type == 'location':
                            device.location_tags.append(tag_name)
                        elif tag_type == 'owner':
                            device.owner_tags.append(tag_name)
                        elif tag_type == 'criticality':
                            device.criticality_tags.append(tag_name)
                        elif tag_type == 'custom':
                            device.custom_tags.append(tag_name)
                        else:
                            logger.warning(f'Bad tags with weird type {tag_type} '
                                           f'__ {str(tag_name)} in device {device_raw}')
                    except Exception:
                        logger.exception(f'Problem adding tag {tag}')
        except Exception:
            logger.exception(f'Problem parsing tags')

        device.set_raw(device_raw)
        return device
