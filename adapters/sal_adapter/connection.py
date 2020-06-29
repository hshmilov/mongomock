import logging
from collections import defaultdict

from sal_adapter.consts import MAX_NUMBER_OF_DEVICES, MACHINES_URL_PREFIX, INVENTORIES_URL_PREFIX, URL_BASE_PREFIX, \
    INVENTORY_KEY
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class SalConnection(RESTConnection):
    """ rest client for Sal adapter """

    def __init__(self, *args, public_key: str, private_key: str, **kwargs):
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

        self._public_key = public_key
        self._private_key = private_key

    def _connect(self):
        if not self._private_key or not self._public_key:
            raise RESTException('No Public Key or Private Key')

        try:
            self._session_headers['publickey'] = self._public_key
            self._session_headers['privatekey'] = self._private_key
            self._get('machines')

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def _get_inventories(self):
        """ Creates and return a mapping/dict in the format of machine_id: [inventory, inventory, ...] """
        try:
            inventories = defaultdict(list)
            response = self._get(INVENTORIES_URL_PREFIX)
            if not (isinstance(response, dict) and
                    isinstance(response.get('results'), list)):
                logger.warning(f'Received invalid response while getting inventories. {response}')
                return {}

            total_inventories = response.get('count')
            logger.info(f'Total inventories is {total_inventories}, max is {MAX_NUMBER_OF_DEVICES}')

            if isinstance(total_inventories, int):
                total_inventories = max(total_inventories, MAX_NUMBER_OF_DEVICES)
            else:
                total_inventories = MAX_NUMBER_OF_DEVICES
            inventories_counter = 0

            for inventory in response.get('results') or []:
                if isinstance(inventory, dict) and inventory.get('machine'):
                    inventories[inventory.get('machine')].append(inventory)
                    inventories_counter += 1

            next_page = response.get('next')
            while next_page and inventories_counter <= total_inventories:
                try:
                    response = self._get(next_page, force_full_url=True)
                    if not (isinstance(response, dict) and
                            isinstance(response.get('results'), list)):
                        logger.warning(f'Received invalid response while getting inventories. {response}')
                        break
                    for inventory in response.get('results') or []:
                        if isinstance(inventory, dict) and inventory.get('machine'):
                            inventories[inventory.get('machine')].append(inventory)
                            inventories_counter += 1

                    next_page = response.get('next')
                except Exception:
                    logger.warning(f'Failed getting next page for inventories, got {response}')
                    break

            logger.info(f'Finished inventories, Got {inventories_counter} out of {total_inventories}.')
            return inventories
        except Exception as e:
            logger.exception(f'Invalid request made while paginating inventories for devices')
            return {}

    def _paginated_device_get(self):
        try:
            inventories = self._get_inventories()

            devices_counter = 0
            response = self._get(MACHINES_URL_PREFIX)
            if not (isinstance(response, dict) and
                    isinstance(response.get('results'), list)):
                logger.warning(f'Received invalid response while paginating. {response}')
                return

            total_devices = response.get('count')
            if isinstance(total_devices, int):
                total_devices = min(total_devices, MAX_NUMBER_OF_DEVICES)
            else:
                total_devices = MAX_NUMBER_OF_DEVICES

            for machine in response.get('results') or []:
                if isinstance(machine, dict) and machine.get('id'):
                    # Injecting a list of inventories (extra data of inventories) to the device data dict
                    machine[INVENTORY_KEY] = inventories.get(machine.get('id'))
                yield machine
                devices_counter += 1

            next_page = response.get('next')
            while next_page and devices_counter <= total_devices:
                try:
                    response = self._get(next_page, force_full_url=True)
                    if not (isinstance(response, dict) and
                            isinstance(response.get('results'), list)):
                        logger.warning(f'Received invalid response while paginating. {response}')
                        break
                    for machine in response.get('results') or []:
                        if isinstance(machine, dict) and machine.get('id'):
                            # Injecting a list of inventories (extra data of inventories) to the device data dict
                            machine[INVENTORY_KEY] = inventories.get(machine.get('id'))
                        yield machine
                        devices_counter += 1

                    next_page = response.get('next')
                except Exception:
                    logger.warning(f'Failed getting next page for devices, got {response}')
                    break

            logger.info(f'Finished machines pagination, Got {devices_counter} out of {total_devices} devices')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
