import datetime
import logging
import time
import zipfile
import json
from collections import defaultdict

from axonius.clients.flexnet.consts import TOKEN_URL, DEVICES_URL, FILES_URL, MAX_NUMBER_OF_DEVICES, \
    ASSETS_URL, DEVICE_PER_PAGE, MAX_WAIT_FOR_DEVICES, INVENTORIES_URL, INVENTORY_TYPE, DEVICE_TYPE, BASE_URL, \
    TOKEN_TIMEOUT_MIN, TYPE_FIELD, ASSET_FIELD, SLEEP_TIME_SEC, COMPLETED_STATUS
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class FlexnetConnection(RESTConnection):
    """ rest client for Flexnet adapter """

    def __init__(self, refresh_token: str, organization_id: str, *args, **kwargs):
        super().__init__(*args, url_base_prefix=BASE_URL.format(organization_id=organization_id),
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token_timeout = None
        self._refresh_token = refresh_token
        self._token = None
        self._organization_id = organization_id

    def _set_token(self):
        if self._token_timeout and self._token_timeout > datetime.datetime.now():
            return

        body_params = {
            'grant_type': 'refresh_token',
            'refresh_token': self._refresh_token
        }
        response = self._post(TOKEN_URL, body_params=body_params, force_full_url=True)
        if not isinstance(response, dict):
            raise RESTException(f'Invalid response returned: {response}')

        self._token = response.get('token') or response.get('access_token')
        logger.debug(f'token response: {response}')
        self._token_timeout = datetime.datetime.now() + datetime.timedelta(minutes=TOKEN_TIMEOUT_MIN)

        self._session_headers['Authorization'] = f'Bearer {self._token}'

    def _connect(self):
        if not self._refresh_token:
            raise RESTException('No refresh token')

        try:
            self._set_token()

            self._post(DEVICES_URL)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        self._set_token()
        time.sleep(SLEEP_TIME_SEC)
        return super()._do_request(*args, **kwargs)

    def _get_assets_by_computer_id(self):
        assets_by_computer_id = defaultdict(list)
        try:
            url_params = {
                'limit': DEVICE_PER_PAGE,
                'offset': 0
            }

            while url_params['offset'] <= MAX_NUMBER_OF_DEVICES:
                response = self._get(ASSETS_URL, url_params=url_params)
                if not (isinstance(response, dict) and
                        isinstance(response.get('values'), list)):
                    logger.warning(f'Response not in the correct format: {response}')
                    return assets_by_computer_id

                for asset in response.get('values'):
                    if not (isinstance(asset, dict) and
                            isinstance(asset.get('metadata'), dict) and
                            asset.get('metadata').get('computerId') is not None):
                        logger.warning(f'asset not in the correct format: {asset}')
                        continue
                    assets_by_computer_id[asset.get('metadata').get('computerId')].append(asset)

                if len(response.get('values')) == 0:
                    logger.info('Finished paginating on assets')
                    break

                url_params['offset'] += DEVICE_PER_PAGE
                if url_params['offset'] >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Got max {MAX_NUMBER_OF_DEVICES} assets')
                    break

            logger.info(f'Got total of {len(assets_by_computer_id)} assets')
        except Exception as e:
            logger.exception(f'Invalid request made while paginating assets')

        return assets_by_computer_id

    def _get_devices(self):
        try:
            total_fetched_devices = 0
            assets_by_computer_id = self._get_assets_by_computer_id()

            response = {}
            device_status = None
            total_devices_tries = 0
            while device_status != COMPLETED_STATUS:
                response = self._post(DEVICES_URL)
                if not (isinstance(response, dict) and
                        isinstance(response.get('data'), dict)):
                    logger.warning(f'Received invalid response for devices: {response}')
                    return
                device_status = response.get('data').get('status')
                total_devices_tries += 1
                if total_devices_tries >= MAX_WAIT_FOR_DEVICES:
                    logger.error('Timeout waiting for devices to finish.')
                    return

            if not response.get('data').get('path'):
                logger.warning(f'Received invalid response for devices: {response}')
                return

            device_path = response.get('data').get('path')
            response = self._get(FILES_URL.format(file_name=device_path),
                                 use_json_in_response=False, return_response_raw=True)

            try:
                with zipfile.ZipFile(response.content) as zip_file:
                    json_name = zip_file.namelist()[0]
                    with zip_file.open(json_name) as json_file:
                        devices = json.loads(json_file.read())
            except Exception as e:
                logger.error(f'Couldn\'t open Response as zip and read json file: {response}')
                return

            if not isinstance(devices, list):
                logger.error(f'Devices is not in the correct format: {devices}')
                return

            for device in devices:
                if not isinstance(device, dict):
                    logger.error(f'Device is not in the correct format: {device}')
                    continue
                device[ASSET_FIELD] = assets_by_computer_id.get(device.get('computerId'))
                device[TYPE_FIELD] = DEVICE_TYPE
                yield device
                total_fetched_devices += 1
                if total_fetched_devices >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Got Max devices {total_fetched_devices} / {len(devices)}')
                    break

            logger.info(f'Got total of {total_fetched_devices} devices')
        except Exception:
            logger.exception(f'Invalid request made while getting devices')
            raise

    def _paginated_get_inventories(self):
        try:
            total_inventories = 0

            url_params = {
                'limit': DEVICE_PER_PAGE,
                'offset': 0
            }

            while url_params['offset'] <= MAX_NUMBER_OF_DEVICES:
                response = self._get(INVENTORIES_URL, url_params=url_params)
                if not (isinstance(response, dict) and
                        isinstance(response.get('values'), list)):
                    logger.warning(f'Response not in the correct format: {response}')
                    return

                for inventory in response.get('values'):
                    if not isinstance(inventory, dict):
                        logger.warning(f'Inventory not in the correct format: {inventory}')
                        continue
                    inventory[TYPE_FIELD] = INVENTORY_TYPE
                    yield inventory
                    total_inventories += 1

                if len(response.get('values')) == 0:
                    logger.info('Finished paginating on inventories')
                    break

                url_params['offset'] += DEVICE_PER_PAGE
                if url_params['offset'] >= MAX_NUMBER_OF_DEVICES:
                    logger.info(f'Got max {MAX_NUMBER_OF_DEVICES} inventories')
                    break
            logger.info(f'Got total of {total_inventories} inventories')
        except Exception as e:
            logger.exception(f'Invalid request made while getting devices')
            raise

    def get_device_list(self):
        try:
            yield from self._get_devices()
        except RESTException as err:
            logger.exception(str(err))

        try:
            yield from self._paginated_get_inventories()
        except RESTException as err:
            logger.exception(str(err))
