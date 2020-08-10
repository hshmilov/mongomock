import logging

from axonius.clients.rest.connection import RESTConnection, RestList, RestDict
from axonius.clients.rest.exception import RESTException
from .consts import MAX_NUMBER_OF_DEVICES, MAX_NUMBER_OF_USERS, DEVICES_URL, USERS_URL, DATACENTER_URL, CABINET_URL

logger = logging.getLogger(f'axonius.{__name__}')


class OpendcimConnection(RESTConnection):
    """ rest client for Opendcim adapter """

    def __init__(self, *args, version=None, user_id=None, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._version = version
        self._user_id = user_id

    def _connect(self):
        if not (self._user_id and self._apikey):
            raise RESTException('No user id or api key')

        try:
            self._session_headers['UserID'] = self._user_id
            self._session_headers['APIKey'] = self._apikey

            self._get(DEVICES_URL)
        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_devices(self):
        try:
            number_of_devices = 0
            response = self._get(DEVICES_URL, response_type=dict)
            devices = RestList(response.get('device', expected_type=list), expected_type=dict)

            data_centers_by_id = self._get_datacenters_by_id()
            cabinets_by_id = self._get_cabinets_by_id()

            for device in devices:
                device = RestDict(device)
                if number_of_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.warning(f'Reached max devices: {number_of_devices}, left: {len(device) - number_of_devices}')
                    break
                cabinet_id = device.get('Cabinet', expected_type=int)
                cabinet = cabinets_by_id.get(str(cabinet_id), expected_type=dict)
                device['extra_cabinet'] = cabinet
                device['extra_datacenter'] = data_centers_by_id.get(cabinet.get('DataCenterID'), expected_type=dict)

                yield device
                number_of_devices += 1

        except Exception:
            logger.exception(f'Invalid request made while fetching devices')
            raise

    def _get_datacenters_by_id(self):
        datacenters_by_id = RestDict()
        try:
            response = self._get(DATACENTER_URL, response_type=dict)
            datacenters = RestList(response.get('datacenter', expected_type=list), expected_type=dict)

            for datacenter in datacenters:
                datacenter = RestDict(datacenter)
                try:
                    datacenter_id = datacenter.get('DataCenterID', expected_type=str, should_raise=True)
                    datacenters_by_id[datacenter_id] = datacenter
                except ValueError:
                    continue
        except Exception:
            logger.exception(f'Invalid request made while fetching data centers')
        return datacenters_by_id

    def _get_cabinets_by_id(self):
        cabinets_by_id = RestDict()
        try:
            response = self._get(CABINET_URL, response_type=dict)
            cabinets = RestList(response.get('cabinet', expected_type=list), expected_type=dict)

            for cabinet in cabinets:
                cabinet = RestDict(cabinet)
                try:
                    cabinet_id = cabinet.get('CabinetID', expected_type=str, should_raise=True)
                    cabinets_by_id[cabinet_id] = cabinet
                except ValueError:
                    continue
        except Exception:
            logger.exception(f'Invalid request made while fetching data centers')
        return cabinets_by_id

    def get_device_list(self):
        try:
            yield from self._get_devices()
        except RESTException as err:
            logger.exception(str(err))
            raise

    def _get(self, *args, **kwargs):
        response = super()._get(*args, **kwargs)

        if response.get('error'):
            error_code = response.get('errorcode')
            message = response.get('message')
            raise RESTException(f'Error while doing GET request. Error code: {error_code}, Message: {message}')
        return response

    def _get_users(self):
        try:
            number_of_users = 0
            response = self._get(USERS_URL, response_type=dict)
            users = RestList(response.get('people', expected_type=list), expected_type=dict)

            for user in users:
                if number_of_users >= MAX_NUMBER_OF_USERS:
                    logger.warning(f'Reached max users: {number_of_users}, left: {len(users) - number_of_users}')
                    break
                yield user
                number_of_users += 1

        except Exception as err:
            logger.exception(f'Invalid request made while fetching users {str(err)}')
            raise

    def get_user_list(self):
        try:
            yield from self._get_users()
        except RESTException as err:
            logger.exception(str(err))
            raise
