import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List
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


class CrowdStrikeConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, headers={'Accept': 'application/json'})
        self.last_token_fetch = None
        self.requests_count = 0

    def refresh_access_token(self, force=False):
        if not self.last_token_fetch or (self.last_token_fetch + timedelta(minutes=20) < datetime.now()) or force:
            logger.debug(f'Refreshing access token after {self.requests_count} requests')
            response = self._post('oauth2/token', use_json_in_body=False,
                                  body_params={'client_id': self._username,
                                               'client_secret': self._password})
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
                logger.error(f'Error getting with args {str(args)}')
                time.sleep(consts.RETRIES_SLEEP_TIME)
                self.refresh_access_token()
                retries += 1
                if retries >= consts.REQUEST_RETRIES:
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
                logger.error('Error getting device groups')

    def get_devices_data(self, devices_ids: List[str], should_get_policies: bool) -> List[Dict]:
        """
        Get devices data from crowdstrike api endpoint: devices/entities/devices/v1
        :param should_get_policies: get policies data for devices
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
        try:
            self.get_devices_groups(devices_data)
        except Exception:
            logger.exception(f'Error getting devices groups')
        return devices

    def get_devices_ids(self, offset: int, devices_per_page: int) -> dict:
        """
        Get devices ids from crowdstrike api
        :param offset: paging offset
        :param devices_per_page: devices per page
        :return:
        """
        logger.debug(f'Getting devices offset {offset}, devices per page: {devices_per_page}')
        return self.__get('devices/queries/devices/v1',
                          url_params={'limit': devices_per_page, 'offset': offset},
                          do_basic_auth=not self._got_token)

    # pylint: disable=arguments-differ
    def get_device_list(self, should_get_policies):
        """
        Get devices data list from CrowdStrike Api
        """
        offset = 0
        devices_per_page = consts.DEVICES_PER_PAGE
        try:
            response = self.get_devices_ids(offset, devices_per_page)
            offset += response['meta']['pagination']['offset']
            self.requests_count += 1
            total_count = response['meta']['pagination']['total']
        except Exception:
            logger.exception(f'Cant get total count')
            raise RESTException('Cant get total count')
        devices_per_page = int(consts.DEVICES_PER_PAGE_PERCENTAGE / 100 * total_count)
        # check if devices_per_page is not too big or too small
        if devices_per_page > consts.MAX_DEVICES_PER_PAGE:
            devices_per_page = consts.MAX_DEVICES_PER_PAGE
        if devices_per_page < consts.DEVICES_PER_PAGE:
            devices_per_page = consts.DEVICES_PER_PAGE

        devices = self.get_devices_data(response['resources'], should_get_policies)
        yield from devices['resources']
        while offset < total_count and offset < consts.MAX_NUMBER_OF_DEVICES:
            try:
                response = self.get_devices_ids(offset, devices_per_page)
                devices = self.get_devices_data(response['resources'], should_get_policies)
                yield from devices['resources']
                self.requests_count += 2
                if self._got_token and self.requests_count >= consts.REFRESH_TOKEN_REQUESTS:
                    self.refresh_access_token()
            except Exception:
                logger.exception(f'Problem getting offset {offset}')
            offset += devices_per_page
