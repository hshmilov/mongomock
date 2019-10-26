import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from bigfix_inventory_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class BigfixInventoryConnection(RESTConnection):
    """ rest client for BigfixInventory adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if (not self._username or not self._password) and (not self._apikey):
            raise RESTException('No username or password and No API Token')
        if not self._apikey:
            response = self._post('get_token', body_params={'user': self._username, 'password': self._password})
            if not response.get('token'):
                raise RESTException(f'Bad login response: {response}')
            self._apikey = response['token']
        self._get('sam/v2/computers?columns[]=id&columns[]=bigfix_id&columns[]=computer_group_id&columns[]=name&'
                  'columns[]=dns_name&columns[]=ip_address&columns[]=os&columns[]=os_type&columns[]=first_seen&'
                  'columns[]=last_seen&columns[]=is_deleted&columns[]=deletion_date&columns[]=is_managed_by_vm_manager&'
                  f'token={self._apikey}&limit={DEVICE_PER_PAGE}&offset=0')

    # pylint: disable=too-many-nested-blocks
    def _get_sw_dict(self):
        sw_dict = dict()
        try:
            offset = 0
            response = self._get('sam/v2/software_instances?columns[]=computer_id&columns[]=product_publisher_name&'
                                 'columns[]=product_name&columns[]=product_release&'
                                 f'token={self._apikey}&limit={DEVICE_PER_PAGE}&offset={offset}')
            total = response.get('total')
            logger.info(f'Total sw is {total}')
            for app_raw in (response.get('rows') or []):
                if app_raw.get('computer_id'):
                    if app_raw.get('computer_id') not in sw_dict:
                        sw_dict[app_raw.get('computer_id')] = []
                    sw_dict[app_raw.get('computer_id')].append(app_raw)
            offset = DEVICE_PER_PAGE
            while offset < min(MAX_NUMBER_OF_DEVICES, total):
                try:
                    response = self._get('sam/v2/software_instances?'
                                         'columns[]=computer_id&columns[]=product_publisher_name&'
                                         'columns[]=product_name&columns[]=product_release&'
                                         f'token={self._apikey}&limit={DEVICE_PER_PAGE}&offset={offset}')
                    if not response.get('rows'):
                        break
                    for app_raw in (response.get('rows') or []):
                        if app_raw.get('computer_id'):
                            if app_raw.get('computer_id') not in sw_dict:
                                sw_dict[app_raw.get('computer_id')] = []
                            sw_dict[app_raw.get('computer_id')].append(app_raw)
                    offset += DEVICE_PER_PAGE
                except Exception:
                    logger.exception(f'Problem at offset {offset}')
                    break
        except Exception:
            logger.exception('Problem getting dict')
        return sw_dict

    def get_device_list(self):
        sw_dict = self._get_sw_dict()
        offset = 0
        response = self._get('sam/v2/computers?columns[]=id&columns[]=bigfix_id&'
                             'columns[]=computer_group_id&columns[]=name&'
                             'columns[]=dns_name&columns[]=ip_address&columns[]=os&'
                             'columns[]=os_type&columns[]=first_seen&'
                             'columns[]=last_seen&columns[]=is_deleted&columns[]=deletion_date&'
                             'columns[]=is_managed_by_vm_manager&'
                             f'token={self._apikey}&limit={DEVICE_PER_PAGE}&offset={offset}')
        total = response.get('total')
        if total is None:
            logger.error(f'bad response: {response}')
            raise RESTException(f'Error in response')
        logger.info(f'Total number is {total}')
        for device_raw in response.get('rows'):
            yield device_raw, sw_dict
        offset = DEVICE_PER_PAGE
        while offset < min(MAX_NUMBER_OF_DEVICES, total):
            try:
                response = self._get('sam/v2/computers?columns[]=id&columns[]=bigfix_id&'
                                     'columns[]=computer_group_id&columns[]=name&'
                                     'columns[]=dns_name&columns[]=ip_address&columns[]=os&'
                                     'columns[]=os_type&columns[]=first_seen&'
                                     'columns[]=last_seen&columns[]=is_deleted&columns[]=deletion_date&'
                                     'columns[]=is_managed_by_vm_manager&'
                                     f'token={self._apikey}&limit={DEVICE_PER_PAGE}&offset={offset}')
                if not response.get('rows'):
                    break
                for device_raw in response.get('rows'):
                    yield device_raw, sw_dict
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at offset {offset}')
                break
