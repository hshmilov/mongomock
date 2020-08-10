import json
import logging
import time
from collections import defaultdict
from typing import Type, List

from axonius.clients.rest.connection import RESTConnection, DEFAULT_429_SLEEP_TIME
from axonius.clients.rest.exception import RESTException
from .consts import URL_AUTH_SUFFIX, URL_DEVICES_SUFFIX, URL_USERS_SUFFIX, URL_HARDWARE_FIELDS, URL_SYSTEM_FIELDS, \
    URL_HARDWARE_REPORT, URL_SYSTEM_REPORT, MAX_NUMBER_OF_USERS, MAX_NUMBER_OF_DEVICES, URL_ANTI_VIRUS, \
    URL_COMPUTER_REPORT, REPORT_MAX_SIZE

logger = logging.getLogger(f'axonius.{__name__}')


class LogmeinConnection(RESTConnection):
    """ rest client for Logmein adapter """

    def __init__(self, *args, company_id: str = None, pre_shared_key: str = None, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._company_id = company_id
        self._pre_shared_key = pre_shared_key

    def _connect(self):
        if not (self._company_id and self._pre_shared_key):
            raise RESTException('No company id or pre shared key')

        try:
            self._session_headers['Authorization'] = json.dumps(
                {'companyId': self._company_id, 'psk': self._pre_shared_key})
            response = self._get(URL_AUTH_SUFFIX)
            if not response.get('success'):
                message = f'Authentication failed. company id: {self._company_id}, response: {response}'
                logger.warning(message)
                raise RESTException(message)

            self._get(URL_DEVICES_SUFFIX)
            self._get(URL_USERS_SUFFIX)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_devices(self):
        try:
            total_devices = 0
            response = self._get(URL_DEVICES_SUFFIX)
            hosts = response.get('hosts')
            if not (hosts and isinstance(hosts, list)):
                logger.warning(f'Response does not contain hosts in the correct format. Response: {response}')
                return
            hardware_fields = self._get(URL_HARDWARE_FIELDS, response_type=list)
            system_fields = self._get(URL_SYSTEM_FIELDS, response_type=list)
            avs_by_id = self._get_avs_by_id()

            host_ids = [host.get('id') for host in hosts if isinstance(host, dict) and host.get('id')]
            hardware_details = self._get_report_details(host_ids, URL_HARDWARE_REPORT, hardware_fields)
            system_details = self._get_report_details(host_ids, URL_SYSTEM_REPORT, system_fields)
            computer_report = self._get_computer_report(host_ids)

            for host in hosts:
                if not isinstance(host, dict):
                    logger.warning(f'Received invalid host type while iterating hosts {host}')
                    continue

                host_id = host.get('id')
                if not host_id:
                    logger.warning(f'host id doesn\'t exist. host: {host}')
                    continue

                host['extra_hardware_details'] = hardware_details.get(str(host_id))
                host['extra_system_details'] = system_details.get(str(host_id))
                host['extra_computer_details'] = computer_report.get(host_id, {})
                host['extra_avs'] = avs_by_id.get(host_id, {})

                total_devices += 1
                yield host
                if total_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.info(
                        f'Exceeded max devices: max {MAX_NUMBER_OF_DEVICES}, left: {len(hosts) - total_devices}')
                    break

            logger.info(f'Got total of {total_devices} devices')
        except RESTException as err:
            logger.exception(str(err))
            raise

    def get_device_list(self):
        try:
            yield from self._get_devices()
        except Exception as err:
            logger.exception(str(err))
            raise

    def _get_users(self):
        try:
            total_users = 0
            response = self._get(URL_USERS_SUFFIX)
            master_account_holder_user = response.get('mahData')
            if isinstance(master_account_holder_user, dict):
                master_account_holder_user['is_master_account_holder'] = True
                total_users += 1
                yield master_account_holder_user

            users = response.get('usersData')
            if not (users and isinstance(users, list)):
                logger.warning(f'Response does not contain usersData in the correct format. Response: {response}')
                return
            for user in users:
                if not isinstance(user, dict):
                    logger.debug(f'Received invalid user type while iterating users {user}')
                    continue

                total_users += 1
                yield user
                if total_users >= MAX_NUMBER_OF_USERS:
                    logger.info(
                        f'Exceeded max users: max {MAX_NUMBER_OF_USERS}, left: {len(users) + 1 - total_users}')
                    break

            logger.info(f'Got total of {total_users} users')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating users {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._get_users()
        except RESTException as err:
            logger.exception(str(err))
            raise

    # pylint: disable=arguments-differ
    def _do_request(self, method: str, name: str, *args, response_type: Type = dict, **kwargs):
        """
        This function overrides _do_request from RestConnection.
        Do request with the parameters and in case of '429' error it wait and tries again.
        '429' error means there are too many requests at the same time, and we need to wait
         60 seconds before trying to send the next request.

        :param method: the request type to do.
        :param name: url for the request.
        :param args: additional arguments.
        :param response_type: response type expected from this request, dict by default.
        :param kwargs: keyword additional arguments.
        :return: response to this request.
        """
        try:
            response = super(LogmeinConnection, self)._do_request(method, name, *args, **kwargs)
        except Exception as e:
            if 'too many requests' in str(e).lower() or '429' in str(e):
                time.sleep(DEFAULT_429_SLEEP_TIME)
                response = super(LogmeinConnection, self)._do_request(method, name, *args, **kwargs)
            else:
                raise
        if not isinstance(response, response_type):
            logger.warning(f'Response not in the expected format {response}')
            return response_type()
        return response

    def _get_report_details(self, host_ids: List[int], url_report: str, fields: List[str]):
        hosts = {}
        try:
            body_params = {'hostIds': host_ids, 'fields': fields}
            response = self._post(url_report, body_params=body_params)

            token = response.get('token')
            if token is None:
                logger.exception(f'token wasn\'t found while looking for system details. Response: {response}')
                return {}

            for i in range(0, int(len(host_ids) / REPORT_MAX_SIZE) + 1):
                response = self._get(f'{url_report}/{token}')
                logger.debug(f'Report response for {url_report}/{token}: {response}')
                if not (response.get('hosts') and isinstance(response.get('hosts'), dict)):
                    logger.debug(f'Received invalid hosts in response while getting report details, {response}')
                    continue
                hosts.update(response.get('hosts'))
                token = response.get('continuation_token')
                if token is None:
                    break
            return hosts
        except Exception as err:
            logger.exception(f'Invalid request made while getting system details {str(err)}')
            return hosts

    def _get_avs_by_id(self):
        avs_by_id = defaultdict(list)
        try:
            response = self._get(URL_ANTI_VIRUS)
            if not (response.get('hosts') and isinstance(response.get('hosts'), list)):
                logger.debug(f'AV response doesn\'t contain hosts: response {response}')
                return avs_by_id

            for av in response.get('hosts'):
                if isinstance(av, dict):
                    if not av.get('hostId'):
                        continue
                    avs_by_id[av.get('hostId')].append((av.get('antiVirusName'), av.get('virusDefinitionVersion')))
            return avs_by_id
        except Exception as err:
            logger.exception(f'Invalid request made while getting avs. {str(err)}')
            return avs_by_id

    def _get_computer_report(self, host_ids: List[str]):
        computer_report_by_id = defaultdict(dict)
        try:
            body_params = {'hostIds': host_ids}
            response = self._post(URL_COMPUTER_REPORT, body_params=body_params, response_type=list)
            for host in response:
                if not (isinstance(host, dict) and 'hostId' in host):
                    continue
                computer_report_by_id[host.get('hostId')] = host
            return computer_report_by_id
        except Exception as err:
            logger.exception(f'Invalid request made while getting computer report {str(err)}')
            return computer_report_by_id
