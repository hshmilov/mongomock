import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from ensilo_adapter import consts


class EnsiloConnection(RESTConnection):

    def _connect(self):
        if self._username is not None and self._password is not None:
            self._get('inventory/list-collectors', do_basic_auth=True)
        else:
            raise RESTException("No user name or password")

    def get_device_list(self):
        try:
            # If we won't get error, let's stop after million devices
            for page_number in range(0, consts.MAX_NUMBER_OF_PAGES):
                device_list_page = self._get(
                    'inventory/list-collectors', url_params={'itemsPerPage': consts.DEVICE_PER_PAGE,
                                                             'pageNumber': str(page_number)},
                    do_basic_auth=True)
                if len(device_list_page) == 0:
                    break
                yield from device_list_page
                logger.info(f"Got {len(device_list_page)} devices at page {page_number}")
        except Exception:
            pass
