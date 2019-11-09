import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from nutanix_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, VM_TYPE, HOST_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


class NutanixConnection(RESTConnection):
    """ rest client for Nutanix adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='/PrismGateway/services/rest/v2.0',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get('vms', do_basic_auth=True, url_params={'offset': 0,
                                                         'length': DEVICE_PER_PAGE,
                                                         'include_vm_nic_config': True,
                                                         'include_vm_disk_config': True})

    def _get_vms(self):
        response = self._get('vms', do_basic_auth=True,
                             url_params={'offset': 0,
                                         'length': DEVICE_PER_PAGE,
                                         'include_vm_nic_config': True,
                                         'include_vm_disk_config': True})
        yield from response.get('entities')
        total_count = (response.get('metadata') or {}).get('count')
        if not total_count:
            raise RESTException(f'Bad Count. Resposne was: {response}')
        offset = DEVICE_PER_PAGE
        while offset < min(MAX_NUMBER_OF_DEVICES, total_count):
            try:
                response = self._get('vms', do_basic_auth=True, url_params={'offset': offset,
                                                                            'length': DEVICE_PER_PAGE,
                                                                            'include_vm_nic_config': True,
                                                                            'include_vm_disk_config': True})
                yield from response.get('entities')
                if not response.get('entities'):
                    break
                offset += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem with offset {offset}')
                break

    def _get_hosts(self):
        response = self._get('hosts', do_basic_auth=True,
                             url_params={'page': 1,
                                         'count': DEVICE_PER_PAGE})
        for host_raw in response.get('entities'):
            try:
                uuid = host_raw.get('uuid')
                if uuid:
                    host_raw['nics_raw'] = self._get(f'hosts/{uuid}/host_nics')
            except Exception:
                logger.exception(f'Problem gettin nics for {host_raw}')
            yield host_raw
        total_count = (response.get('metadata') or {}).get('count')
        if not total_count:
            raise RESTException(f'Bad Count. Resposne was: {response}')
        page = 2
        while (page * DEVICE_PER_PAGE) < min(MAX_NUMBER_OF_DEVICES, total_count):
            try:
                response = self._get('hosts', do_basic_auth=True, url_params={'page': page,
                                                                              'count': DEVICE_PER_PAGE})
                for host_raw in response.get('entities'):
                    try:
                        uuid = host_raw.get('uuid')
                        if uuid:
                            host_raw['nics_raw'] = self._get(f'hosts/{uuid}/host_nics')
                    except Exception:
                        logger.exception(f'Problem gettin nics for {host_raw}')
                    yield host_raw
                if not response.get('entities'):
                    break
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break

    def get_device_list(self):
        for device_raw in self._get_vms():
            yield device_raw, VM_TYPE
        for device_raw in self._get_hosts():
            yield device_raw, HOST_TYPE
