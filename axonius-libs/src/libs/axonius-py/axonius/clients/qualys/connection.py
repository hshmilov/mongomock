import contextlib
import functools
import logging
import io
import csv
import datetime
import ipaddress
import re
from collections import defaultdict
from typing import List, Dict, Optional, Iterable, Generator, Union, Tuple, Set
from urllib.parse import urljoin

from axonius.clients.qualys import consts, xmltodict
from axonius.clients.qualys.consts import JWT_TOKEN_REFRESH, INVENTORY_AUTH_API, MAX_DEVICES, INVENTORY_TYPE, \
    UNSCANNED_IP_TYPE, HOST_ASSET_TYPE, REPORT_URL_PREFIX, HOST_URL_PREFIX, UNSCANNED_IP_URL_PREFIX
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.consts import get_default_timeout
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')
'''
In this connection we target the VM module (and probably PC later on).
These modules have a rate limit - by default of 2 connections through api v2.0 or 300 api requests an hour.
For the sake of the user - if the next api request is allowed within the next 30 seconds we wait and try again.
'''


# pylint: disable=logging-format-interpolation


class IteratorCounter:
    def __init__(self,
                 message,
                 start_value=0,
                 threshold=50):
        self._message = message
        self._count = start_value
        self._last_printed_value = self._count
        self._threshold = threshold

    def add(self, value=1):
        self._count += value

    def print_if_needed(self):
        if self._count - self._last_printed_value >= self._threshold:
            self._last_printed_value = self._count
            self.print()
            return True
        return False

    def print(self):
        logger.info(self._message.format(count=self._count))


# pylint: disable=too-many-instance-attributes
class QualysScansConnection(RESTConnection):

    def __init__(self,
                 *args,
                 request_timeout=None,
                 chunk_size=None,
                 devices_per_page=None,
                 retry_sleep_time=None,
                 max_retries=None,
                 date_filter=None,
                 fetch_from_inventory=False,
                 fetch_report=False,
                 fetch_tickets=False,
                 fetch_unscanned_ips=False,
                 **kwargs):
        """ Initializes a connection to Illusive using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Illusive
        """
        request_timeout = request_timeout or consts.DEFAULT_REQUEST_TIMEOUT
        super().__init__(*args, session_timeout=(get_default_timeout().read_timeout, request_timeout), **kwargs)
        self._permanent_headers = {'X-Requested-With': 'Axonius Qualys Scans Adapter',
                                   'Accept': 'application/json'}
        self._date_filter = date_filter
        self._chunk_size = chunk_size or consts.DEFAULT_CHUNK_SIZE
        self._devices_per_page = devices_per_page or consts.DEVICES_PER_PAGE
        self._retry_sleep_time = retry_sleep_time or consts.RETRY_SLEEP_TIME
        self._max_retries = max_retries or consts.MAX_RETRIES
        self._fetch_from_inventory = fetch_from_inventory
        self._fetch_report = fetch_report
        self._fetch_tickets = fetch_tickets
        self._fetch_unscanned_ips = fetch_unscanned_ips
        self._jwt_token = None
        self._jwt_token_refresh = None
        self._gateway_api = self._get_qualys_gateway(str(self._url))

    def _refresh_jwt_token(self):
        if self._jwt_token_refresh and self._jwt_token_refresh < datetime.datetime.now():
            return
        self._get_inventory_jwt_token()

    @staticmethod
    def _get_qualys_gateway(api_url):
        # prepare gatway_url - https://www.qualys.com/platform-identification/

        # if no endpoint, take default
        if 'qualysapi.qualys' in api_url:
            gateway_replacement = 'gateway.qg1'

        # The rest public ones starts with qualysapi.qg#
        elif 'qualysapi.qg' in api_url:
            gateway_replacement = 'gateway'

        # Private platform
        else:
            gateway_replacement = 'qualysgateway'

        return api_url.replace('qualysapi', gateway_replacement)

    def _get_inventory_jwt_token(self):
        try:
            self._session_headers['Content-Type'] = 'application/x-www-form-urlencoded'
            body_params = {
                'username': self._username,
                'password': self._password,
                'token': 'true',
            }
            url = urljoin(self._gateway_api, INVENTORY_AUTH_API)
            token = self._post(url, body_params=body_params, force_full_url=True, use_json_in_body=False,
                               use_json_in_response=False, return_response_raw=False)
            if not (isinstance(token, bytes) and token):
                raise ValueError(f'Got unknown response while getting token {str(token)}')

            self._jwt_token = token.decode('utf-8').strip('"')
            self._jwt_token_refresh = datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_TOKEN_REFRESH)
            self._session_headers = {
                'Authorization': 'Bearer ' + self._jwt_token,
                'Content-Type': 'application/json'
            }
        except Exception as e:
            raise ValueError(f'Error: Failed getting jwt token, invalid request was made. {str(e)}')

    def _connect_inventory(self):
        try:
            self._get_inventory_jwt_token()
            url_params = {
                'pageSize': 1
            }
            url = urljoin(self._gateway_api, '/am/v1/assets/host/filter/list')
            self._post(url, url_params=url_params, force_full_url=True)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials: {str(e)}')

    def _paginated_inventory_get(self):
        try:
            fetched_devices = {}
            total_devices = 0
            url_params = {
                'pageSize': 100
            }
            url = urljoin(self._gateway_api, '/am/v1/assets/host/filter/list')
            self._refresh_jwt_token()
            response = self._post(url, url_params=url_params, force_full_url=True)
            if not (isinstance(response, dict) and isinstance(response.get('assetListData'), dict)):
                logger.warning(f'Received invalid response {response}')
                return

            asset_list_data = response.get('assetListData')
            if not isinstance(asset_list_data.get('asset'), list):
                logger.warning(f'Received invalid response, no assets found {response}')
                return

            for device in asset_list_data.get('asset'):
                if isinstance(device, dict) and device.get('assetId'):
                    fetched_devices[device.get('assetId')] = True
                yield device, INVENTORY_TYPE
                total_devices += 1

            while response.get('hasMore') and total_devices < MAX_DEVICES:
                if not response.get('lastSeenAssetId'):
                    logger.warning(f'Failed paginate all assets {response}')
                    break

                url_params['lastSeenAssetId'] = response.get('lastSeenAssetId')
                self._refresh_jwt_token()
                response = self._post(url, url_params=url_params, force_full_url=True)
                if not (isinstance(response, dict) and isinstance(response.get('assetListData'), dict)):
                    logger.warning(f'Received invalid response while pagination {response}')
                    break

                for device in asset_list_data.get('asset'):
                    # There is a bug in the pagination mechanism
                    # https://discussions.qualys.com/thread/20713-pagination-problem-limited-records
                    # Checking if the pagination works and the paginate result got new devices
                    if isinstance(device, dict) and device.get('assetId'):
                        if fetched_devices.get(device.get('assetId')):
                            # Pop existing devices that already been yield
                            fetched_devices.pop(device.get('assetId'))
                            continue
                        fetched_devices[device.get('assetId')] = True
                    yield device
                    total_devices += 1

                # No new devices fetched
                if not len(fetched_devices):
                    logger.debug(f'Stopping pagination, got response with 0 new devices')
                    break

            logger.info(f'Finish paginate assets, got {total_devices}')
        except Exception as err:
            logger.exception(f'Invalid request made, {str(err)}')
            raise

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')

        if self._fetch_from_inventory:
            self._connect_inventory()
        else:
            self._get_device_count()

    def _prepare_get_hostassets_request_params(self, start_offset):
        params = {
            'ServiceRequest': {
                'preferences': {
                    'startFromOffset': start_offset,
                    'limitResults': self._devices_per_page
                },
            }
        }
        if self._date_filter:
            # filter by 'last_seen' greater then
            params['ServiceRequest']['filters'] = {
                'Criteria': [{
                    'field': 'lastVulnScan',
                    'operator': 'GREATER',
                    'value': self._date_filter,
                }],
            }
        return {'name': 'qps/rest/2.0/search/am/hostasset/',
                'body_params': params,
                'do_basic_auth': True}

    def get_device_id_data(self, device_id):
        response = self._get(f'qps/rest/2.0/get/am/hostasset/{device_id}', do_basic_auth=True)
        if not isinstance(response, dict):
            raise RESTException(f'Bad Response not as dict: {str(response)}')
        if 'ServiceResponse' not in response:
            raise RESTException(f'Bad Response without ServiceResponse: {str(response)}')
        response = response['ServiceResponse']
        if 'data' not in response:
            raise RESTException(f'Bad response with not data: {str(response)}')
        if not isinstance(response['data'], list) or not response['data']:
            raise RESTException(f'Bad response with bad data: {str(response)}')
        return response['data'][0]

    def _get_device_count(self):
        params = {
            'ServiceRequest': {
            }
        }
        if self._date_filter:
            # filter by 'last_seen' greater then
            params['ServiceRequest']['filters'] = {
                'Criteria': [{
                    'field': 'lastVulnScan',
                    'operator': 'GREATER',
                    'value': self._date_filter,
                }],
            }
        exception_count = 0
        while True:
            try:
                result = self._post('qps/rest/2.0/count/am/hostasset', body_params=params, do_basic_auth=True)
                if not (result.get('ServiceResponse') or {}).get('count'):
                    raise RuntimeError(f'Response is {result}')
                break
            except Exception as e:
                logger.warning(f'Exception {exception_count} while fetching count error :{e}')
                exception_count += 1
                if exception_count >= consts.FETCH_EXCEPTION_THRESHOLD:
                    raise

        return result['ServiceResponse']['count']

    def _get_hostassets_by_requests(self, requests):
        for request_id, response in enumerate(self._async_post(requests, chunks=self._chunk_size,
                                                               retry_on_error=True,
                                                               max_retries=self._max_retries,
                                                               retry_sleep_time=self._retry_sleep_time)):
            try:
                if isinstance(response, Exception):
                    logger.error(f'{request_id} - Got Exception: {response}')
                    continue

                service_response = response.get('ServiceResponse') or {}
                data = service_response.get('data')
                if not data:
                    logger.error(f'{request_id} - no data. Response is {service_response}')
                    continue

                yield (request_id, data)
                self._yielded_devices_count.add(len(data))
                self._yielded_devices_count.print_if_needed()
            except Exception:
                logger.exception(f'{request_id} - Failed to deliver: {response}')

    def _get_hostassets(self):
        logger.info('Starting to fetch')
        count = self._get_device_count()
        self._yielded_devices_count = IteratorCounter(f'Got {{count}} devices so far out of {count}', threshold=100)
        logger.info(f'device count is {count}')

        offsets = range(1, count + 1, self._devices_per_page)
        requests = [self._prepare_get_hostassets_request_params(offset) for offset in offsets]

        hosts = self._get_hosts()

        report = {}
        tickets = {}
        if self._fetch_report:
            report = self._get_report()
        if self._fetch_tickets:
            tickets = self._get_tickets()

        # we try to fetch each page max exception threshold.
        # if we got data back we remove it from the next round
        # if we got all responses back we stop

        for i in range(1, consts.FETCH_EXCEPTION_THRESHOLD + 1):
            logger.info(f'Aync round number {i}, sending {len(requests)} requests')
            success_indices = []
            for index, devices in self._get_hostassets_by_requests(requests):
                for device in devices:
                    if isinstance(device, dict) and isinstance(device.get('HostAsset'), dict) and \
                            device.get('HostAsset').get('address'):
                        ip = device.get('HostAsset').get('address')
                        if hosts.get(ip):
                            device['HostAsset']['extra_host'] = hosts.get(ip)
                        if tickets.get(ip):
                            device['HostAsset']['extra_tickets'] = tickets.get(ip)
                        if report.get(ip):
                            device['HostAsset']['extra_report'] = report.get(ip)
                    yield device

                success_indices.append(index)

            requests = [request for i, request in enumerate(requests) if i not in success_indices]
            if not requests:
                break
        else:
            logger.error(f'Lost {len(requests) * self._devices_per_page} devices')

    def get_device_list(self):
        try:
            if self._fetch_unscanned_ips:
                yield from self._get_unscanned_ips()
        except Exception as e:
            logger.exception(f'Problem getting unscanned ips {str(e)}')

        try:
            if self._fetch_from_inventory:
                yield from self._paginated_inventory_get()
            else:
                for device_raw in self._get_hostassets():
                    yield device_raw, HOST_ASSET_TYPE
        except Exception:
            logger.exception(f'Problem getting hostassets')

    def add_assets_by_hostname(self, hosts: List):
        """seems like add assets by hostname isn"t implemented yet"""
        # https://github.com/paragbaxi/qualysapi/blob/master/qualysapi/api_actions.py
        raise NotImplementedError()

    def add_assets_by_ip(self, ips: List):
        """Permissions - A Manager has permissions to add IP addresses.
           A Unit Manager can add IP addresses when the “Add assets” permission is enabled in their account.
           Users with other roles (Scanner, Reader, Auditor) do not have permissions to add IP addresses."""
        try:
            ips = ','.join(ips)
            resp = self._post('api/2.0/fo/asset/ip/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'add'},
                              body_params={'ips': ips, 'enable_vm': 1})
            resp = xmltodict.parse(resp)
            text = resp['SIMPLE_RETURN']['RESPONSE']['TEXT']
            return text == 'IPs successfully added to Vulnerability Management', text
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return False, ''

    def _get_unscanned_ips(self):
        try:
            resp = self._get(UNSCANNED_IP_URL_PREFIX,
                             do_basic_auth=True,
                             use_json_in_body=False,
                             use_json_in_response=False,
                             url_params={'action': 'list'})
            resp = xmltodict.parse(resp)

            if not (isinstance(resp.get('IP_LIST_OUTPUT'), dict) and
                    isinstance(resp.get('IP_LIST_OUTPUT').get('RESPONSE'), dict) and
                    isinstance(resp.get('IP_LIST_OUTPUT').get('RESPONSE').get('IP_SET'), dict) and
                    isinstance(resp['IP_LIST_OUTPUT']['RESPONSE']['IP_SET'].get('IP'), list)):
                raise Exception(f'Received invalid response while fetching hosts. {resp}')

            for unscanned_ip in resp['IP_LIST_OUTPUT']['RESPONSE']['IP_SET'].get('IP') or []:
                yield unscanned_ip, UNSCANNED_IP_TYPE

            if not resp.get('IP_LIST_OUTPUT').get('RESPONSE').get('IP_SET').get('IP_RANGE'):
                logger.warning(f'No IP ranges in IP List Output')
                return

            ips_range = resp['IP_LIST_OUTPUT']['RESPONSE']['IP_SET']['IP_RANGE']
            if isinstance(ips_range, str):
                ips_range = [ips_range]
            if not isinstance(ips_range, list):
                logger.warning(f'Received invalid ips_range {ips_range}')
                return

            for unscanned_ip_range in ips_range:
                start_ip, end_ip = unscanned_ip_range.split('-')
                start_ip = ipaddress.IPv4Address(start_ip)
                end_ip = ipaddress.IPv4Address(end_ip)
                ip_address_summarize = ipaddress.summarize_address_range(start_ip, end_ip)
                for ip_addresses in ip_address_summarize:
                    for ip_address in ip_addresses:
                        yield str(ip_address), UNSCANNED_IP_TYPE

        except Exception as e:
            logger.warning(f'Failed getting unscanned IPs with {e}')
            return

    def get_asset_by_ip(self, ips: List):
        """Permissions - A Manager has permissions to add IP addresses.
           A Unit Manager can add IP addresses when the “Add assets” permission is enabled in their account.
           Users with other roles (Scanner, Reader, Auditor) do not have permissions to add IP addresses."""
        try:
            ips = ','.join(ips)
            resp = self._post('api/2.0/fo/asset/ip/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'list'},
                              body_params={'ips': ips})
            resp = xmltodict.parse(resp)
            text = resp['IP_LIST_OUTPUT']['RESPONSE']['IP_SET']['IP']
            return text
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return []

    def _get_hosts(self):
        logger.info('Starting to fetch hosts')
        hosts = defaultdict(list)
        total_hosts = 0
        try:
            resp = self._get(HOST_URL_PREFIX,
                             do_basic_auth=True,
                             use_json_in_body=False,
                             use_json_in_response=False,
                             url_params={'action': 'list', 'details': 'All/AGs'})
            resp = xmltodict.parse(resp)

            if not (isinstance(resp, dict) and
                    isinstance(resp.get('HOST_LIST_OUTPUT'), dict) and
                    isinstance(resp.get('HOST_LIST_OUTPUT').get('RESPONSE'), dict) and
                    isinstance(resp.get('HOST_LIST_OUTPUT').get('RESPONSE').get('HOST_LIST'), dict) and
                    isinstance(resp['HOST_LIST_OUTPUT']['RESPONSE']['HOST_LIST'].get('HOST'), list)):
                raise Exception(f'Received invalid response while fetching hosts. {resp}')

            for host in resp['HOST_LIST_OUTPUT']['RESPONSE']['HOST_LIST'].get('HOST') or []:
                ip = host.get('IP')
                if ip is not None:
                    hosts[ip].append(host)
                    total_hosts += 1

            if not (isinstance(resp.get('HOST_LIST_OUTPUT').get('RESPONSE').get('WARNING'), dict) and
                    resp.get('HOST_LIST_OUTPUT').get('RESPONSE').get('WARNING').get('URL')):
                logger.debug(f'No more hosts in _get_hosts()')
                return hosts

            while resp['HOST_LIST_OUTPUT']['RESPONSE']['WARNING']['URL']:
                url = resp['HOST_LIST_OUTPUT']['RESPONSE']['WARNING']['URL']
                resp = self._get(url,
                                 do_basic_auth=True,
                                 use_json_in_body=False,
                                 use_json_in_response=False,
                                 force_full_url=True)
                resp = xmltodict.parse(resp)

                if not (isinstance(resp, dict) and
                        isinstance(resp.get('HOST_LIST_OUTPUT'), dict) and
                        isinstance(resp.get('HOST_LIST_OUTPUT').get('RESPONSE'), dict) and
                        isinstance(resp.get('HOST_LIST_OUTPUT').get('RESPONSE').get('HOST_LIST'), dict) and
                        isinstance(resp['HOST_LIST_OUTPUT']['RESPONSE']['HOST_LIST'].get('HOST'), list)):
                    logger.warning(f'Received invalid response while paginated hosts. {resp}')
                    # Breaking to retrieve all the information from the first pagination
                    break

                for host in resp['HOST_LIST_OUTPUT']['RESPONSE']['HOST_LIST'].get('HOST') or []:
                    ip = host.get('IP')
                    if ip is not None:
                        hosts[ip].append(host)
                        total_hosts += 1

                if not (isinstance(resp.get('HOST_LIST_OUTPUT').get('RESPONSE').get('WARNING'), dict) and
                        resp.get('HOST_LIST_OUTPUT').get('RESPONSE').get('WARNING').get('URL')):
                    logger.debug(f'No more pagination in _get_hosts()')
                    break

            logger.info(f'Got total of {total_hosts} hosts')
            return hosts
        except Exception as e:
            logger.warning(f'Failed getting hosts after {total_hosts} with {e}', exc_info=True)
            return hosts

    # pylint: disable=too-many-branches
    def _get_report(self):
        logger.info('Starting to fetch report')
        report_result = {}
        try:
            # List all the reports
            resp = self._get(REPORT_URL_PREFIX,
                             do_basic_auth=True,
                             use_json_in_body=False,
                             use_json_in_response=False,
                             url_params={'action': 'list'})
            resp = xmltodict.parse(resp)

            if not (isinstance(resp, dict) and
                    isinstance(resp.get('REPORT_LIST_OUTPUT'), dict) and
                    isinstance(resp.get('REPORT_LIST_OUTPUT').get('RESPONSE'), dict) and
                    isinstance(resp.get('REPORT_LIST_OUTPUT').get('RESPONSE').get('REPORT_LIST'), dict) and
                    isinstance(resp['REPORT_LIST_OUTPUT']['RESPONSE']['REPORT_LIST'].get('REPORT'), list)):
                raise Exception(f'Received invalid response while fetching authentication report. {resp}')

            # Getting the most up to date report
            report_id = None
            report_date = None
            for report in resp['REPORT_LIST_OUTPUT']['RESPONSE']['REPORT_LIST'].get('REPORT') or []:
                if not isinstance(report, dict):
                    continue

                # We take a regular Authentication Report (Most up to date)
                if report.get('ID') and report.get('LAUNCH_DATETIME') and report.get(
                        'TYPE') == 'Authentication' and report.get('OUTPUT_FORMAT') == 'CSV':
                    if not report_id:
                        report_id = report.get('ID')
                        report_date = report.get('LAUNCH_DATETIME')
                    elif report_date < report.get('LAUNCH_DATETIME'):
                        report_id = report.get('ID')
                        report_date = report.get('LAUNCH_DATETIME')

            if not report_id:
                logger.debug(f'Failed to find Authentication Report '
                             f'{resp["REPORT_LIST_OUTPUT"]["RESPONSE"]["REPORT_LIST"].get("REPORT")}')
                return report_result

            # Fetching the report (Downloading) -> CSV Bytes
            resp = self._get(REPORT_URL_PREFIX,
                             do_basic_auth=True,
                             use_json_in_body=False,
                             use_json_in_response=False,
                             url_params={'action': 'fetch', 'id': report_id})

            decode_resp = resp.decode('utf-8')  # bytes -> str
            # Each report has SUMMARY and RESULTS, We only want the RESULTS info
            re_resp = re.search('RESULTS\\r\\n(.*)', decode_resp, re.DOTALL)
            if not re_resp:
                logger.debug(f'Failed finding report results for {resp}')
                return report_result
            resp = re_resp.group(1)
            resp = io.StringIO(resp)  # str -> file object

            # will read the upper-most line as the headers (fields name)
            reader = csv.DictReader(resp)

            for row in reader:
                if not (isinstance(row, dict) and row.get('Host IP')):
                    logger.debug(f'Received invalid row {row}')
                    continue
                report_result[row.get('Host IP')] = row

            logger.info(f'Got Report with {len(report_result.keys())} IPs')
            return report_result
        except Exception as e:
            logger.warning(f'Failed getting report with {e}', exc_info=True)
            return report_result

    def _get_tickets(self):
        logger.info('Starting to fetch tickets')
        tickets = defaultdict(list)
        total_tickets = 0
        try:
            resp = self._get('msp/ticket_list.php',
                             do_basic_auth=True,
                             use_json_in_body=False,
                             use_json_in_response=False,
                             url_params={'states': 'OPEN'})
            resp = xmltodict.parse(resp)

            if not (isinstance(resp, dict) and
                    isinstance(resp.get('REMEDIATION_TICKETS'), dict) and
                    isinstance(resp.get('REMEDIATION_TICKETS').get('TICKET_LIST'), dict) and
                    isinstance(resp['REMEDIATION_TICKETS']['TICKET_LIST'].get('TICKET'), list)):
                raise Exception(f'Received invalid response while fetching tickets. {resp}')

            tickets_list = resp.get('REMEDIATION_TICKETS').get('TICKET_LIST').get('TICKET') or []
            if isinstance(tickets_list, list):
                for ticket in tickets_list:
                    if not isinstance(ticket, dict):
                        logger.warning(f'Ticket not a dict, got {ticket}')
                        continue
                    if not (isinstance(ticket.get('DETECTION'), dict) and ticket.get('DETECTION').get('IP')):
                        logger.debug(f'Ticket without an IP Address {ticket}')
                        continue

                    tickets[ticket.get('DETECTION').get('IP')].append(ticket)
                    total_tickets += 1

            last_ticket = resp.get('REMEDIATION_TICKETS').get('@last')
            while last_ticket:
                resp = self._get('msp/ticket_list.php',
                                 do_basic_auth=True,
                                 use_json_in_body=False,
                                 use_json_in_response=False,
                                 url_params={'states': 'OPEN', 'since_ticket_number': last_ticket})
                resp = xmltodict.parse(resp)

                if not (isinstance(resp, dict) and
                        isinstance(resp.get('REMEDIATION_TICKETS'), dict) and
                        isinstance(resp.get('REMEDIATION_TICKETS').get('TICKET_LIST'), dict) and
                        isinstance(resp['REMEDIATION_TICKETS']['TICKET_LIST'].get('TICKET'), list)):
                    logger.warning(f'Received invalid response while paginate tickets {resp}')
                    # Breaking to retrieve all the information from the first pagination
                    break

                tickets_list = resp.get('REMEDIATION_TICKETS').get('TICKET_LIST').get('TICKET') or []
                if isinstance(tickets_list, list):
                    for ticket in tickets_list:
                        if not isinstance(ticket, dict):
                            logger.warning(f'Ticket is not a dict, got {ticket}')
                            continue
                        if not (isinstance(ticket.get('DETECTION'), dict) and ticket.get('DETECTION').get('IP')):
                            logger.debug(f'Ticket without an IP Address {ticket}')
                            continue

                        tickets[ticket.get('DETECTION').get('IP')].append(ticket)
                        total_tickets += 1

                last_ticket = resp.get('REMEDIATION_TICKETS').get('@last')

            logger.info(f'Got total of {total_tickets} tickets')
            return tickets
        except Exception as e:
            logger.warning(f'Failed getting tickets after {total_tickets} with {e}', exc_info=True)
            return tickets

    def get_asset_group_id_by_title(self, title):
        try:
            resp = self._post('api/2.0/fo/asset/group/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'list'},
                              body_params={'title': title, 'show_attributes': 'ID'})
            resp = xmltodict.parse(resp)
            return resp['ASSET_GROUP_LIST_OUTPUT']['RESPONSE']['ID_SET']['ID']
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return None

    def delete_group(self, id_):
        try:
            resp = self._post('api/2.0/fo/asset/group/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'delete'},
                              body_params={'id': id_})
            resp = xmltodict.parse(resp)
            text = resp['SIMPLE_RETURN']['RESPONSE']['TEXT']
            return text == 'Asset Group Deleted Successfully', text
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return False, ''

    def create_group(self, title, ips: List = None, hostnames: List = None):
        try:
            if not ips:
                ips = []
            if not hostnames:
                hostnames = []

            ips = ','.join(ips)
            hostnames = ','.join(hostnames)

            body_params = {'title': title}
            if ips:
                body_params['ips'] = ips

            if hostnames:
                body_params['dns_names'] = hostnames

            resp = self._post('api/2.0/fo/asset/group/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'add'},
                              body_params=body_params)
            resp = xmltodict.parse(resp)

            text = resp['SIMPLE_RETURN']['RESPONSE']['TEXT']
            return text == 'Asset Group successfully added.', text
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return False, ''

    def _pagination_body_generator(self, filter_criteria_list: Optional[Iterable[dict]] = None):
        # ignore initial empty response
        record_count = 0
        has_more = True
        while has_more:
            last_response = (yield self._prepare_service_request(filter_criteria_list=filter_criteria_list,
                                                                 start_offset=record_count))
            record_count += last_response.get('count', 0)
            has_more = (last_response.get('count') and last_response.get('hasMoreRecords', '') == 'true')

    def _search_tags(self, fields: Optional[List[str]] = None) -> Generator[dict, None, None]:
        """Permissions required - Managers with full scope, other users must have
           Access Permission “API Access”"""
        try:
            resp = None
            query_params_str = f'?fields={",".join(fields)}' if fields else ''
            body_params_gen = self._pagination_body_generator()
            # Note: This loop ends with StopIteration exception
            while True:
                body_params = body_params_gen.send(resp)
                resp = self._post(f'qps/rest/2.0/search/am/tag{query_params_str}',
                                  do_basic_auth=True,
                                  use_json_in_body=True,
                                  use_json_in_response=False,
                                  body_params=body_params,
                                  extra_headers={'Accept': 'application/xml'})
                resp = xmltodict.parse(resp)
                service_response = self._handle_qualys_response(resp)
                tags_list = service_response['data']['Tag']
                if not isinstance(tags_list, list):
                    tags_list = [tags_list]
                yield from tags_list
        except StopIteration:
            pass
        except Exception:
            logger.exception(f'Failed search_tags')
            return

    def _search_hosts(self, filter_criteria_list: Optional[Iterable[dict]] = None,
                      fields: Optional[Iterable[str]] = None) -> Generator[dict, None, None]:
        """Permissions required - Managers with full scope, other users must have these
           permissions: Access Permission “API Access” and Asset Management
           Permission “Read Asset”"""

        try:
            logger.info(f'searching hosts by the following criterias: {filter_criteria_list}')

            resp = None
            query_params_str = f'?fields={",".join(fields)}' if fields else ''
            body_params_gen = self._pagination_body_generator(filter_criteria_list=filter_criteria_list)
            # Note: This loop ends with StopIteration exception
            while True:
                body_params = body_params_gen.send(resp)
                resp = self._post(f'qps/rest/2.0/search/am/hostasset{query_params_str}',
                                  do_basic_auth=True,
                                  use_json_in_body=True,
                                  use_json_in_response=False,
                                  body_params=body_params,
                                  extra_headers={'Accept': 'application/xml'})
                resp = xmltodict.parse(resp)
                service_response = self._handle_qualys_response(resp)

                # determine whether multiple results returned
                host_assets = service_response['data']['HostAsset']
                if not isinstance(host_assets, list):
                    host_assets = [host_assets]
                yield from host_assets

        except StopIteration:
            return
        except Exception:
            logger.exception(f'Failed searching hosts - body params: {body_params}')
            return

    def list_tag_ids_by_name(self) -> Dict[str, str]:
        """ see _search_tags """
        return {tag_dict['name']: tag_dict['id'] for tag_dict in self._search_tags(fields=['id', 'name'])}

    def iter_tags_by_host_id(self, host_id_list: Optional[Iterable[str]] = None) \
            -> Generator[Tuple[str, Iterable[dict]], None, None]:
        """ see _search_hosts """

        criteria_list = []
        if host_id_list:
            criteria_list.append(self._generate_filter_criteria_for_host_ids(host_id_list))

        hosts = self._search_hosts(filter_criteria_list=criteria_list,
                                   fields=['id', 'tags.list.TagSimple.id', 'tags.list.TagSimple.name'])
        if not hosts:
            return

        for host_dict in hosts:
            tags = host_dict.get('tags', {}).get('list', {}).get('TagSimple', [])
            if not isinstance(tags, list):
                tags = [tags]
            yield host_dict['id'], tags

    def add_host_existing_tags(self, host_id_list: Iterable[str], tag_ids_to_add: Iterable[str]):
        """Permissions: see _update_hostasset"""
        logger.info(f'Adding existing tags {tag_ids_to_add} to hosts {host_id_list}')
        return self._update_hostasset_tags(host_id_list, 'add', tag_ids_to_add)

    def remove_host_tags(self, host_id_list: Iterable[str], tag_ids_to_remove: Iterable[str]):
        """Permissions: see _update_hostasset"""
        logger.info(f'Removing tags {tag_ids_to_remove} from hosts {host_id_list}')
        return self._update_hostasset_tags(host_id_list, 'remove', tag_ids_to_remove)

    def _update_hostasset_tags(self, host_id_list: Iterable[str],
                               operation_name: str, tag_id_list: Iterable[Union[str, int]]) -> dict:
        """Permissions: see _update_hostasset"""
        return self._update_hostasset(
            host_id_list,
            request_body={'data': {'HostAsset': {'tags': {operation_name: {
                'TagSimple': [{'id': tag_id} for tag_id in tag_id_list]
            }}}}})

    def _update_hostasset(self, host_id_list: Iterable[str], request_body: dict) -> dict:
        """Permissions required - Managers with full scope, other users must have the
           requested assets in their scope and these permissions: Access Permission
           “API Access” and Asset Management Permission “Update Asset”"""

        logger.info(f'Updating hosts {host_id_list} with request body: {request_body}')

        body_params = self._prepare_service_request(
            request_body=request_body,
            filter_criteria_list=[self._generate_filter_criteria_for_host_ids(host_id_list)])

        try:
            # pylint: disable=invalid-string-quote
            resp = self._post(f'qps/rest/2.0/update/am/hostasset',
                              do_basic_auth=True,
                              use_json_in_body=True,
                              use_json_in_response=False,
                              body_params=body_params,
                              extra_headers={'Accept': 'application/xml'})
            resp = xmltodict.parse(resp)
            service_response = self._handle_qualys_response(resp)
            return service_response
        except Exception:
            logger.exception(f'Failed updating hosts {host_id_list}')
            return {}

    def create_tag(self, tag_name: str, parent_tag_id: Optional[str] = None):
        """Permissions required - Managers with full scope, other users must have these
           permissions: Access Permission “API Access”, Tag Permission “Create User
           Tag”, Tag Permission “Modify Dynamic Tag Rules” (to create a dynamic tag)"""

        logger.info(f'Creating tag {tag_name} with parent {parent_tag_id}')

        # prepare request
        additional_fields_dict = {}
        if parent_tag_id:
            additional_fields_dict = {'parentTagId': parent_tag_id}

        body_params = self._prepare_service_request(
            {'data': {'Tag': {'name': tag_name, **additional_fields_dict}}})

        try:
            resp = self._post(f'qps/rest/2.0/create/am/tag',
                              do_basic_auth=True,
                              use_json_in_body=True,
                              use_json_in_response=False,
                              body_params=body_params,
                              extra_headers={'Accept': 'application/xml'})
            resp = xmltodict.parse(resp)
            service_response = self._handle_qualys_response(resp)
            created_tag_dict = service_response.get('data', {}).get('Tag', {})
            logger.debug(f'Created tag {created_tag_dict} successfully')
            return created_tag_dict
        except Exception:
            logger.exception(f'Failed creating tag {tag_name}')
            return {}

    def delete_tags(self, tag_id_list: Iterable[str]):
        """Permissions required - Managers with full scope, other users must have these
           permissions: Access Permission “API Access” and Tag Permission “Delete User Tag”"""
        logger.info(f'Deleting tags {tag_id_list}')

        body_params = self._prepare_service_request(
            filter_criteria_list=[self._generate_filter_criteria('id', 'IN', ','.join(tag_id_list))])

        try:
            resp = self._post(f'qps/rest/2.0/delete/am/tag',
                              do_basic_auth=True,
                              use_json_in_body=True,
                              use_json_in_response=False,
                              body_params=body_params,
                              extra_headers={'Accept': 'application/xml'})
            resp = xmltodict.parse(resp)
            service_response = self._handle_qualys_response(resp)
            return (data_dict.get('Tag') for data_dict in service_response.get('data', {})
                    if data_dict.get('Tag'))
        except Exception:
            logger.exception(f'Failed deleting tags {tag_id_list}')
            return []

    def create_tags(self, names_list: Iterable[str], parent_tag_id: Optional[str] = None) \
            -> Tuple[Dict[str, str], Optional[str]]:
        """ see create_tag """

        logger.info(f'Creating tags {names_list} with parent {parent_tag_id}')

        created_tag_ids_by_name = {}  # type: Dict[str, str]
        for tag_name in names_list:
            created_tag_dict = self.create_tag(tag_name, parent_tag_id=parent_tag_id)
            if not created_tag_dict:
                logger.error(f'Tag "{tag_name}" creation failed')
                return created_tag_ids_by_name, tag_name

            created_tag_ids_by_name[tag_name] = created_tag_dict['id']
        return created_tag_ids_by_name, None

    def _prepare_service_request(self,
                                 request_body: Optional[dict] = None,
                                 filter_criteria_list: Optional[Iterable[dict]] = None,
                                 start_offset: Optional[int] = None) -> dict:

        params_dict = {}
        service_request = params_dict.setdefault('ServiceRequest', request_body or {})

        if start_offset:
            service_request['preferences'] = {
                'startFromOffset': start_offset,
                'limitResults': self._devices_per_page
            }

        # handle filters
        criteria_list = []
        if filter_criteria_list:
            criteria_list.extend(filter_criteria_list)

        if self._date_filter:
            # filter by 'last_seen' greater than
            criteria_list.append({
                'field': 'lastVulnScan',
                'operator': 'GREATER',
                'value': self._date_filter,
            })

        if criteria_list:
            service_request.setdefault('filters', {}).setdefault('Criteria', []).extend(criteria_list)

        return params_dict

    @staticmethod
    def _generate_filter_criteria(field: str, operator_name: str, value: str):
        return {'field': field, 'operator': operator_name, 'value': value}

    def _generate_filter_criteria_for_host_ids(self, host_id_list: Iterable[str]):
        return self._generate_filter_criteria('id', 'IN', ','.join(host_id_list))

    @staticmethod
    def _handle_qualys_response(response: bytes):
        service_response = response.get('ServiceResponse')
        response_code = (service_response or {}).get('responseCode')
        if not (service_response and response_code):
            raise RESTException('Malformed response - missing ServiceResponse')
        if response_code != 'SUCCESS':
            raise RESTException(f'failed with code {response_code},'
                                f' message: {(service_response.get("responseErrorDetails") or {}).get("errorMessage")}')
        return service_response

    # pylint: disable=too-many-locals,too-many-statements,too-many-return-statements
    def add_tags_to_qualys_ids(self, qualys_dict: dict) -> Tuple[bool, Optional[str]]:
        """
        :param qualys_dict: {
            'qualys_ids': List[str],
            'tags_to_add': List[str],
            'parent_tag_name': Optional[str]
        }
        returns: Either:
            (False, message) for generic_fail
            (True, None) for generic_success
        """
        try:

            qualys_ids: List[str] = qualys_dict.get('qualys_ids')
            if not (isinstance(qualys_ids, list) and qualys_ids):
                raise ValueError(f'Invalid or No Qualys IDs given: {qualys_ids}')

            tags_to_add: List[str] = qualys_dict.get('tags_to_add')
            if not (isinstance(tags_to_add, list) and tags_to_add):
                raise ValueError(f'Invalid or No tags given: {tags_to_add}')
            requested_tags_set = set(tags_to_add)
            logger.debug(f'Unique requested tags: {requested_tags_set}')

            parent_tag_name: Optional[str] = qualys_dict.get('parent_tag_name')
            if not (isinstance(parent_tag_name, str) or parent_tag_name is None):
                raise ValueError(f'Invalid parent tag name given: {parent_tag_name}')

            with contextlib.ExitStack() as revert_stack:  # type: contextlib.ExitStack

                tag_ids_by_name = self.list_tag_ids_by_name()
                logger.debug(f'Located tags: {tag_ids_by_name}')
                if not (isinstance(tag_ids_by_name, dict) and tag_ids_by_name):
                    message = 'Failed retrieving existing tags'
                    logger.error(message)
                    return False, message

                # create missing tags
                created_tag_ids = set()  # type: Set[str]
                tag_names_to_create = requested_tags_set - set(tag_ids_by_name.keys())
                if tag_names_to_create:

                    # if parent given and doesnt exist - fail all devices
                    if parent_tag_name and parent_tag_name not in tag_ids_by_name:
                        message = f'Failed locating parent tag "{parent_tag_name}"'
                        logger.error(message)
                        return False, message

                    # create the tags and push a revert removal operation
                    parent_tag_id = tag_ids_by_name.get(parent_tag_name)
                    created_tag_ids_by_name, failed_tag_name = self.create_tags(tag_names_to_create,
                                                                                parent_tag_id=parent_tag_id)
                    # Note - delete_tags would also remove the tags from any
                    #        hostasset they've been successfully assigned to
                    # pylint: disable=no-member
                    revert_stack.callback(functools.partial(self.delete_tags, created_tag_ids_by_name.values()))
                    if failed_tag_name:
                        logger.error(f'The following tag failed to create: {failed_tag_name}')
                        return False, f'Failed Creating tag "{failed_tag_name}"'
                    tag_ids_by_name.update(created_tag_ids_by_name)
                    created_tag_ids.update(created_tag_ids_by_name.values())

                # add tags to hosts and push a revert tags restore operation
                preoperation_tags_by_host = dict(self.iter_tags_by_host_id(qualys_ids))
                missing_tags_post_creation = [tag_name for tag_name in requested_tags_set
                                              if tag_name not in tag_ids_by_name]
                if len(missing_tags_post_creation) > 0:
                    logger.error(f'The following tags was not found post-creation: {missing_tags_post_creation}')
                    return False, f'Failed locating tags "{",".join(missing_tags_post_creation)}" post-creation.'

                requested_tag_ids = {tag_ids_by_name[tag_name] for tag_name in requested_tags_set}
                _ = self.add_host_existing_tags(qualys_ids, requested_tag_ids)
                for host_id in qualys_ids:
                    # we push separate revert operation per host due to their potential different state
                    preop_tag_dicts = preoperation_tags_by_host.get(host_id)
                    if not preop_tag_dicts:
                        logger.debug(f'failed to locate host {host_id} in existing tags, ditching revert operation.')
                        continue
                    # compute revertible tags for removal - any requested tag that wasn't created and didn't pre-exist.
                    revertible_tags = (requested_tag_ids - created_tag_ids
                                       - {tag_dict['id'] for tag_dict in preop_tag_dicts})
                    if revertible_tags:
                        logger.debug(f'Appending revert tag removal operation for host {host_id}'
                                     f' for revertible tags {revertible_tags}')
                        # pylint: disable=no-member
                        revert_stack.callback(functools.partial(self.remove_host_tags,
                                                                [host_id], revertible_tags))

                # re-list tags to make sure they were added
                missing_tag_names_by_host_id = {
                    host_id: (requested_tags_set - {tag_dict['name'] for tag_dict in tags_dicts})
                    for host_id, tags_dicts in self.iter_tags_by_host_id(qualys_ids)
                }  # type: Dict[str, Set[str]]
                logger.debug(f'Missing tags by host: {missing_tag_names_by_host_id}')

                # if any of the hosts has a missing tag, fail everything
                hosts_missing_tags = {host_id: missing_tags for
                                      host_id, missing_tags in missing_tag_names_by_host_id.items()
                                      if len(missing_tags) > 0}
                if len(hosts_missing_tags) > 0:
                    logger.warning(f'Tag addition verification failed: {hosts_missing_tags}')
                    return False, 'Failed tag addition verification'
                    # Note - Revert happens here in LIFO order #

                # everything went well - cancel revert stack
                logger.info('Operation Succeeded, flushing revert stack')
                # pylint: disable=no-member
                _ = revert_stack.pop_all()

            return True, None
        except Exception:
            logger.exception(f'Problem with action add tag')
            return False, 'Unexpected error'
