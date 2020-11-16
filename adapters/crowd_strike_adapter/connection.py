import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from funcy import chunks

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException, RESTRequestException
from crowd_strike_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')

# XXX: For some reason this file doesn't ignore logging-fstring-interpolation
# although we got it in pylintrc ignore. add disable for it, and disable the disable warning
# pylint: disable=I0021
# pylint: disable=W1203
# api doc: https://assets.falcon.crowdstrike.com/support/api/swagger.html

PoliciesType = Dict[str, List]
MAX_PAGES_PROTECTION = 1000000


class CrowdStrikeConnection(RESTConnection):
    def __init__(self, *args, member_cid=None, **kwargs):
        super().__init__(*args, **kwargs, headers={'Accept': 'application/json'})
        self.last_token_fetch = None
        self.requests_count = 0
        self._member_cid = member_cid

    def refresh_access_token(self, force=False):
        if not self.last_token_fetch or (self.last_token_fetch + timedelta(minutes=20) < datetime.now()) or force:
            logger.debug(f'Refreshing access token after {self.requests_count} requests')
            body_params = {'client_id': self._username,
                           'client_secret': self._password}
            if self._member_cid:
                body_params['member_cid'] = self._member_cid
            response = self._post('oauth2/token', use_json_in_body=False,
                                  body_params=body_params)
            token = response['access_token']
            self._session_headers['Authorization'] = f'Bearer {token}'
            self.last_token_fetch = datetime.now()
            self.requests_count = 0

    def _connect(self):
        if not self._username or not self._password is not None:
            raise RESTException('No user name or API key')
        try:
            self.refresh_access_token(force=True)  # just try
            self._got_token = True
            logger.info('oauth success')
        except Exception:
            logger.exception('Oauth failed')
            self._got_token = False
        self._get('devices/queries/devices/v1',
                  do_basic_auth=not self._got_token,
                  url_params={'limit': consts.DEVICES_PER_PAGE, 'offset': 0})

    def __get(self, *args, **kwargs):
        """
        Calls _get but tries a couple of times.
        :param args: args
        :param kwargs: kwargs
        :return:
        """
        retries = 0
        while retries < consts.REQUEST_RETRIES:
            try:
                return self._get(*args, **kwargs)
            except RESTRequestException as e:
                time.sleep(consts.RETRIES_SLEEP_TIME)
                self.refresh_access_token()
                retries += 1
                if retries >= consts.REQUEST_RETRIES:
                    logger.error(f'Error getting URL after {consts.REQUEST_RETRIES} retries with args {str(args)}')
                    raise e

    @staticmethod
    def _add_policy(policies: PoliciesType, device: dict, policy: dict):
        """
        Add device to a list in the policies dictionary
        :param policies: policies dictionary
        :param device: device data
        :param policy: policy data
        :return: None
        """
        if not policy:
            return
        policy_id = policy.get('policy_id')
        if policy_id:
            policies.setdefault(policy_id, []).append(device)

    def get_policies(self, policies: PoliciesType, p_type: consts.PolicyTypes):
        """
        Get Policies data from crowdstrike api and fill policy data for each device
        :param policies: policies dictionary: {policy_id:[list_of_devices_that_own_this_policy..]}
        :param p_type: policy type - usually prevention or sensor_update
        :return: None
        """
        if not policies:
            return
        policies_ids = policies.keys()
        req_type = p_type.replace_to_dash()
        policies_data = self.__get(f'policy/entities/{req_type}/v1',
                                   url_params={'ids': policies_ids},
                                   do_basic_auth=not self._got_token)
        logger.debug(f'Got {len(policies_data)} policies')
        resources = policies_data.get('resources')
        if not isinstance(resources, list):
            logger.error(f'Error getting policies data for {policies_ids}')
            return
        for resource in resources:
            try:
                policy_id = resource.get('id', None)
                devices = policies.pop(policy_id)
                for device in devices:
                    device['device_policies'][p_type.value]['data'] = resource
            except Exception:
                logger.exception('Error getting policy resource')
        if len(policies) > 0:
            logger.error(f'Error getting policies: {policies.keys()}')
        policies.clear()

    def get_devices_policies(self, devices_data: dict):
        """
        Get all the policies data for the given devices.
        Usually a lot of devices share the same policies and we dont want to spam the server with unnecessary requests,
        So we will save all the policies ids in a PoliciesType dict and fetch policies data after each chunk of devices.
        :param devices_data:
        :return: None
        """
        # these dicts will hold all the policies and their devices
        prevention_policies = {}
        sensor_update_policies = {}
        for device in devices_data:
            policies = device.get('device_policies')
            if policies is not None:
                prevention = policies.get(consts.PolicyTypes.Prevention.value)
                sensor_update = policies.get(consts.PolicyTypes.SensorUpdate.value)
                # add device policies ids to the policies dictionary
                self._add_policy(prevention_policies, device, prevention)
                self._add_policy(sensor_update_policies, device, sensor_update)
            # if we have reached the max policies length lets get their data
            if len(prevention_policies) == consts.MAX_POLICIES_LENGTH:
                self.get_policies(prevention_policies, consts.PolicyTypes.Prevention)
            if len(prevention_policies) == consts.MAX_POLICIES_LENGTH:
                self.get_policies(prevention_policies, consts.PolicyTypes.SensorUpdate)

        self.get_policies(prevention_policies, consts.PolicyTypes.Prevention)
        self.get_policies(sensor_update_policies, consts.PolicyTypes.SensorUpdate)

    def get_devices_groups(self, devices_data: dict):
        """
        Get devices groups data from the api
        :param devices_data: device data
        :return: None
        """
        groups = {}
        for device in devices_data:
            device_groups = device.get('groups', [])
            for group_id in device_groups:
                groups.setdefault(group_id, []).append(device)
        if not groups:
            return
        group_ids = groups.keys()
        for chunk in chunks(consts.MAX_GROUPS_PER_REQUEST, group_ids):
            try:
                groups_res = self.__get(f'devices/entities/host-groups/v1',
                                        url_params={'ids': chunk},
                                        do_basic_auth=not self._got_token)
                groups_data = groups_res.get('resources', [])
                logger.debug(f'Got {len(groups_data)} groups')
                for group_data in groups_data:
                    group_id = group_data.get('id')
                    if group_id:
                        devices = groups.get(group_id)
                        for device in devices:
                            device.setdefault('groups_data', []).append(group_data)
            except Exception:
                logger.exception('Error getting device groups')

    def get_vulnerabilities_data(self, device_data: dict, vulnerabilities_ids: List[str]) -> None:
        """
        Get vulnerabilities data by vulnerabilities ids
        :param device_data:
        :param vulnerabilities_ids:
        :return:
        """
        device_id = device_data.get('device_id')
        for chunk in chunks(consts.MAX_VULS_PER_REQUEST, vulnerabilities_ids):
            try:
                vul_res = self.__get(f'spotlight/entities/vulnerabilities/v2',
                                     url_params={'ids': chunk},
                                     do_basic_auth=not self._got_token)
                vul_data = vul_res.get('resources', [])
                device_data.setdefault('vulnerabilities', []).extend(vul_data)
            except Exception:
                logger.error(f'Error getting device vulnerabilities for {device_id}')

    def get_device_vulnerabilities(self, device_data: dict) -> None:
        """
        Get device vulnerabilities data from falcon spotlight api
        :param device_data: device data
        :return: None
        """
        device_id = device_data.get('device_id')
        # first request for getting meta data with vulnerabilities data
        device_vulnerabilities = self.__get(f'spotlight/queries/vulnerabilities/v1',
                                            url_params={'filter': f'aid:\'{device_id}\'',
                                                        'limit': consts.VULS_PER_REQUEST},
                                            do_basic_auth=not self._got_token)
        vulnerabilities_ids = device_vulnerabilities.get('resources', [])
        pagination = device_vulnerabilities.get('meta', {}).get('pagination', {})
        total_vulns = pagination.get('total')
        next_page = pagination.get('after')
        vulns_got = len(vulnerabilities_ids)
        self.get_vulnerabilities_data(device_data, vulnerabilities_ids)
        logger.debug(f'Got {vulns_got}/{total_vulns} vulnerabilities for {device_id}')

        while next_page:
            device_vulnerabilities = self.__get(f'spotlight/queries/vulnerabilities/v1',
                                                url_params={'filter': f'aid:\'{device_id}\'',
                                                            'after': next_page,
                                                            'limit': consts.VULS_PER_REQUEST},
                                                do_basic_auth=not self._got_token)
            vulnerabilities_ids = device_vulnerabilities.get('resources', [])
            pagination = device_vulnerabilities.get('meta', {}).get('pagination', {})
            next_page = pagination.get('after')
            vulns_got += len(vulnerabilities_ids)
            self.get_vulnerabilities_data(device_data, vulnerabilities_ids)
            logger.debug(f'Got {vulns_got}/{total_vulns} vulnerabilities for {device_id}')

    def get_devices_data(self, devices_ids: List[str], should_get_policies: bool, should_get_vulnerabilities: bool) -> \
            List[Dict]:
        """
        Get devices data from crowdstrike api endpoint: devices/entities/devices/v1
        :param should_get_policies: get policies data for devices
        :param should_get_vulnerabilities: get vulnerabilities from spotlight api
        :param devices_ids: devices ids
        :return: list of devices
        """
        if len(devices_ids) > consts.MAX_DEVICES_PER_PAGE:
            logger.warning(f'Request too many devices_ids: {devices_ids}, max: {consts.MAX_DEVICES_PER_PAGE}')
        devices = self.__get('devices/entities/devices/v1',
                             url_params={'ids': devices_ids},
                             do_basic_auth=not self._got_token)
        devices_data = devices.get('resources')
        if should_get_policies:
            try:
                self.get_devices_policies(devices_data)
            except Exception:
                logger.exception(f'Error getting devices policies')
        if should_get_vulnerabilities:
            for device_data in devices_data:
                try:
                    self.get_device_vulnerabilities(device_data)
                except Exception:
                    device_id = device_data.get('device_id')
                    logger.exception(f'Error getting device vulnerabilities. device_id: {device_id}')
        try:
            self.get_devices_groups(devices_data)
        except Exception:
            logger.exception(f'Error getting devices groups')
        return devices

    def get_devices_ids(self, offset: int, devices_per_page: int, query: str = None) -> dict:
        """
        Get devices ids from crowdstrike api
        :param offset: paging offset
        :param devices_per_page: devices per page
        :return:
        """
        logger.debug(f'Getting devices offset {offset}, devices per page: {devices_per_page}, query: {str(query)}')
        url_params = {'limit': devices_per_page, 'offset': offset}
        if query:
            url_params['filter'] = query
        return self.__get('devices/queries/devices/v1',
                          url_params=url_params,
                          do_basic_auth=not self._got_token)

    def get_devices_ids_scroll(self, offset: Optional[str], devices_per_page: int, query: str = None) -> dict:
        """
        Get devices ids from crowdstrike api
        :param offset: paging offset
        :param devices_per_page: devices per page
        :return:
        """
        logger.debug(f'Getting devices offset {offset}, devices per page: {devices_per_page}, query: {str(query)}')
        url_params = {'limit': devices_per_page}
        if offset:
            url_params['offset'] = offset
        if query:
            url_params['filter'] = query
        return self.__get('devices/queries/devices-scroll/v1',
                          url_params=url_params,
                          do_basic_auth=not self._got_token)

    # pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
    # pylint: disable=arguments-differ, too-many-boolean-expressions
    def get_device_list(self, should_get_policies, should_get_vulnerabilities, avoid_aws_dups=False):
        """
        Get devices data list from CrowdStrike Api
        """
        # CrowdStrike has a scroll api that supports more than 150,000 devices but it is not open to everyone.
        # try it first
        try:
            response = self.get_devices_ids_scroll(None, 10)
            query_count = response['meta']['pagination']['total']
            logger.info(f'Using scroll api with total devices: {query_count}')
            has_scroll_api = True
        except Exception:
            logger.warning(f'Problem using scroll api, reverting to regular api', exc_info=True)
            has_scroll_api = False

        if has_scroll_api:
            aws_dups_dict = dict()
            try:
                if avoid_aws_dups:
                    for device_raw in self.get_device_list_with_scroll_api(should_get_policies=False,
                                                                           should_get_vulnerabilities=False):
                        hostname = device_raw.get('hostname')
                        dict_id = hostname
                        for key in ['local_ip', 'service_provider_account_id']:
                            dict_id += '_' + (device_raw.get(key) or '')
                        device_id = device_raw.get('device_id')
                        last_seen = device_raw.get('last_seen')
                        if hostname and hostname.startswith('ip-') and hostname.endswith('.compute.internal') \
                                and device_raw.get('service_provider') == 'AWS_EC2':
                            if dict_id not in aws_dups_dict:
                                aws_dups_dict[dict_id] = [device_id, last_seen]
                            if last_seen and not aws_dups_dict[dict_id][1]:
                                aws_dups_dict[dict_id] = [device_id, last_seen]
                            if last_seen and aws_dups_dict[dict_id][1] and last_seen > aws_dups_dict[dict_id][1]:
                                aws_dups_dict[dict_id] = [device_id, last_seen]
            except Exception:
                logger.exception(f'Problem with AWS dups')
            for device_raw in self.get_device_list_with_scroll_api(should_get_policies, should_get_vulnerabilities):
                if avoid_aws_dups:
                    hostname = device_raw.get('hostname')
                    dict_id = hostname
                    for key in ['local_ip', 'service_provider_account_id']:
                        dict_id += '_' + (device_raw.get(key) or '')
                    device_id = device_raw.get('device_id')
                    if hostname and hostname.startswith('ip-') and hostname.endswith('.compute.internal') and \
                            device_raw.get('service_provider') == 'AWS_EC2':
                        if aws_dups_dict.get(dict_id)[0] != device_id:
                            continue
                yield device_raw
            return

        # If that doesn't work then we need to use the 'regular' api.
        # Due to the API's pagination limit (up to 150,000 devices per one query) we have to split the
        # yields for differnet queries.
        try:
            response = self.get_devices_ids(0, 10)
            total_count = response['meta']['pagination']['total']
            logger.info(f'Total count of all assets: {total_count}')
        except Exception:
            logger.exception(f'Can not get initial pagination response')
            raise

        # Yield all hostname that start with A, B, C, etc. Note! this is case in-sensitive.
        letters = [chr(x) for x in range(ord('A'), ord('A') + 26)]
        for letter in letters:
            try:
                yield from self.get_device_list_with_query(
                    should_get_policies,
                    should_get_vulnerabilities,
                    f'hostname:\'{letter}*\''
                )
            except Exception:
                logger.exception(f'Can not yield for letter {letter}')

        # Then, yield from all those who do not start with ascii letters
        try:
            yield from self.get_device_list_with_query(
                should_get_policies,
                should_get_vulnerabilities,
                '+'.join([f'hostname:!\'{letter}*\'' for letter in letters])
            )
        except Exception:
            logger.exception(f'Can not yield not of all letters')

        # Then, yield those who do not have a hostname. This should have been part of the 'not all letters'
        # filter but do this just in case.
        try:
            yield from self.get_device_list_with_query(
                should_get_policies,
                should_get_vulnerabilities,
                'hostname:null'
            )
        except Exception:
            logger.exception(f'Can not yield from hostname null')

    def get_device_list_with_scroll_api(self, should_get_policies, should_get_vulnerabilities):
        try:
            response = self.get_devices_ids_scroll(None, consts.DEVICES_PER_PAGE)
            offset = response['meta']['pagination']['offset']
            self.requests_count += 1
            total_count = response['meta']['pagination']['total']
        except Exception:
            logger.exception(f'Cant get total count')
            raise RESTException('Cant get total count')

        logger.info(f'Devices scroll: got total count of {total_count}')

        devices_per_page = int(consts.DEVICES_PER_PAGE_PERCENTAGE / 100 * total_count)
        # check if devices_per_page is not too big or too small
        if devices_per_page > consts.MAX_DEVICES_PER_PAGE:
            devices_per_page = consts.MAX_DEVICES_PER_PAGE
        if devices_per_page < consts.DEVICES_PER_PAGE:
            devices_per_page = consts.DEVICES_PER_PAGE

        # We have to first pull all resources, then pull the data. The reason being is that
        # the scrolling cursor is active just for 2 minutes, and so we have to make those requests quick enough
        # and not trust get_devices_data which could be slow.
        all_devices_resources = response['resources']

        pages = 0
        while pages < MAX_PAGES_PROTECTION:
            try:
                pages += 1
                response = self.get_devices_ids_scroll(offset, devices_per_page)

                if not response['resources']:
                    break

                all_devices_resources.extend(response['resources'])
                self.requests_count += 2
                if self._got_token and self.requests_count >= consts.REFRESH_TOKEN_REQUESTS:
                    self.refresh_access_token()

                offset = response['meta']['pagination']['offset']
                if not offset:
                    break
            except Exception:
                logger.exception(f'Problem getting device-resources offset {offset}')
                break

        logger.info(f'Got {len(all_devices_resources)} device-ids in {pages} pages. Yielding with data now')

        for chunk in chunks(devices_per_page, all_devices_resources):
            try:
                devices = self.get_devices_data(chunk, should_get_policies, should_get_vulnerabilities)
                yield from devices['resources']

                self.requests_count += 2
                if self._got_token and self.requests_count >= consts.REFRESH_TOKEN_REQUESTS:
                    self.refresh_access_token()

            except Exception:
                logger.exception(f'Problem getting offset {offset}')
                break

    def get_device_list_with_query(self, should_get_policies, should_get_vulnerabilities, query):
        offset = 0
        devices_per_page = consts.DEVICES_PER_PAGE
        try:
            response = self.get_devices_ids(offset, devices_per_page, query)
            offset += response['meta']['pagination']['offset']
            self.requests_count += 1
            total_count = response['meta']['pagination']['total']
        except Exception:
            logger.exception(f'Cant get total count')
            raise RESTException('Cant get total count')

        logger.info(f'Total count for "{str(query)}": {total_count}')

        if total_count > 150000:
            logger.warning(f'Warning - more than 150,000 devices per query! Crowd-Strike API does not support that. '
                           f'Querying up to 150,000.')
            total_count = 150000

        devices_per_page = int(consts.DEVICES_PER_PAGE_PERCENTAGE / 100 * total_count)
        # check if devices_per_page is not too big or too small
        if devices_per_page > consts.MAX_DEVICES_PER_PAGE:
            devices_per_page = consts.MAX_DEVICES_PER_PAGE
        if devices_per_page < consts.DEVICES_PER_PAGE:
            devices_per_page = consts.DEVICES_PER_PAGE

        devices = self.get_devices_data(response['resources'], should_get_policies, should_get_vulnerabilities)
        yield from devices['resources']

        while offset < total_count and offset < consts.MAX_NUMBER_OF_DEVICES:
            try:
                response = self.get_devices_ids(offset, devices_per_page, query)
                devices = self.get_devices_data(response['resources'], should_get_policies, should_get_vulnerabilities)
                yield from devices['resources']
                self.requests_count += 2
                if self._got_token and self.requests_count >= consts.REFRESH_TOKEN_REQUESTS:
                    self.refresh_access_token()
            except Exception:
                logger.exception(f'Problem getting offset {offset}')
            offset += devices_per_page
