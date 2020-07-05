import base64
import logging

from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection
from desktop_central_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class DesktopCentralConnection(RESTConnection):
    def __init__(self, *args, username_domain: str = '', **kwargs):
        super().__init__(*args, **kwargs)
        self._username_domain = username_domain

    def _connect(self):
        if self._username is not None and self._password is not None:
            connection_dict = {'username': self._username,
                               'password': str(base64.b64encode(bytes(self._password, 'utf-8')), encoding='utf-8')}
            if self._username_domain is None:
                connection_dict['auth_type'] = consts.LOCAL_AUTHENTICATION
            else:
                connection_dict['auth_type'] = consts.DOMAIN_AUTHENTICATION
                connection_dict['domainName'] = self._username_domain

            response = self._post('desktop/authentication', body_params=connection_dict)
            if (('message_response' not in response or 'status' not in response or 'message_version' not in response or
                 'message_version' not in response) or (response['status'] != 'success')):
                raise RESTException(f'Unknown connection error in authentication {str(response)}')
            self._session_headers['Authorization'] = response['message_response']['authentication']['auth_data'][
                'auth_token']
        else:
            raise RESTException('No username or password')

    def _get_extra_data_for_page(self, devices, inner_url, raw_name, inner_object_attribute, paged=True):
        def _get_extra_request():
            url_params = {'resid': device_id}
            if paged:
                url_params.update({'page': str(page_sw),
                                   'pagelimit': consts.DEVICES_PER_PAGE})
            return self._get(inner_url,
                             url_params=url_params)

        for device_raw in devices:
            try:
                device_id = device_raw['resource_id']
                page_sw = 1
                sw_raw = _get_extra_request()
                if not sw_raw or not sw_raw.get('message_response'):
                    continue
                device_raw[raw_name] = sw_raw['message_response'][inner_object_attribute]
                if not paged:
                    continue
                sw_pages = sw_raw['message_response']['total']

                for page_sw in range(2, sw_pages + 1):
                    sw_raw = _get_extra_request()
                    if not sw_raw or not sw_raw.get('message_response'):
                        break
                    if not sw_raw['message_response'][inner_object_attribute]:
                        break
                    device_raw[raw_name].extend(sw_raw['message_response'][inner_object_attribute])
            except Exception:
                logger.exception(f'Problem getting sw for {device_raw}')

    def get_device_list(self):
        def _get_devices_from_page():
            response = self._get('som/computers', url_params={'page': page,
                                                              'pagelimit': consts.DEVICES_PER_PAGE})
            devices = response['message_response']['computers']
            self._get_extra_data_for_page(devices, 'inventory/installedsoftware', 'sw_raw', 'installedsoftware')
            self._get_extra_data_for_page(devices, 'patch/systemreport', 'pa_raw', 'systemreport')
            self._get_extra_data_for_page(devices, 'inventory/compdetailssummary', 'sum_raw', 'compdetailssummary',
                                          paged=False)
            total_pages = response['message_response']['total']
            return devices, total_pages

        page = 1
        devices, total_pages = _get_devices_from_page()
        yield from devices
        for page in range(2, total_pages + 1):
            try:
                devices, _ = _get_devices_from_page()
                yield from devices
            except Exception:
                logger.exception(f'Problem getting pgae {page}')
