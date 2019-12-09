import datetime
import logging
import xml.etree.ElementTree as ET


from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from airwave_adapter.consts import DEVICE_PER_PAGE, MAX_NUMBER_OF_DEVICES, CLIENT_TYPE, AP_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


class AirwaveConnection(RESTConnection):
    """ rest client for Airwave adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={},
                         **kwargs)
        self._expires_in = 3599
        self._last_refresh = None

    def _get_device_list_from_query_str(self, query_str):
        self._refresh_token()
        xml_raw = self._get('client_search.xml',
                            url_params={'query': query_str},
                            use_json_in_response=False)
        xml_obj = ET.fromstring(xml_raw)
        if 'amp_client_search' not in xml_obj.tag:
            raise RESTException(f'Bad xml with tag {xml_obj.tag}')
        for record in xml_obj:
            try:
                device_raw = {}
                for xml_property in record:
                    if xml_property.getchildren():
                        device_raw[xml_property.tag] = [child.text for child in xml_property.getchildren()
                                                        if child.tag == 'content']
                    else:
                        device_raw[xml_property.tag] = xml_property.text
                yield device_raw
            except Exception:
                logger.exception(f'Problem at record')

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        destination = '/'
        next_action = ''
        params = {'credential_0': self._username,
                  'credential_1': self._password,
                  'login': 'Log In',
                  'destination': destination,
                  'next_action': next_action}
        self._post('LOGIN', url_params=params, use_json_in_response=False)
        self._last_refresh = datetime.datetime.now()

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._last_refresh = None
        self._refresh_token()
        self._get('api/list_view.json', url_params={'list': 'client_all', 'fv_id': '0', 'page_length': DEVICE_PER_PAGE})

    def _get_api_endpoint(self, api_endpoint):
        self._refresh_token()
        response = self._get('api/list_view.json',
                             url_params={'list': api_endpoint,
                                         'fv_id': '0',
                                         'page_length': DEVICE_PER_PAGE})
        yield from response.get('records')
        total_count = self._get('api/total_count.json',
                                url_params={'list': api_endpoint,
                                            'fv_id': '0'}
                                ).get('total_count')
        total_count = int(total_count)
        logger.info(f'Total Count of {api_endpoint} is {total_count}')
        offset = DEVICE_PER_PAGE
        while offset < min(total_count, MAX_NUMBER_OF_DEVICES) and response.get('has_next') is True:
            try:
                logger.info(f'Offset is {offset}')
                self._refresh_token()
                response = self._get('api/list_view.json',
                                     url_params={'list': api_endpoint,
                                                 'fv_id': '0',
                                                 'page_length': DEVICE_PER_PAGE,
                                                 'start_row': offset})
                yield from response.get('records')
                if len(response.get('records')) < DEVICE_PER_PAGE:
                    break
            except Exception:
                logger.exception(f'Problem with offset {offset}')
            offset += DEVICE_PER_PAGE

    def get_device_list(self):
        for device_raw in self._get_api_endpoint('ap_list'):
            yield device_raw, AP_TYPE

        mac_extra_data_dict = dict()
        for device_raw in self._get_api_endpoint('client_all'):
            try:
                mac = (device_raw.get('mac') or {}).get('value')
                if mac is None:
                    continue
                mac_short = mac[:-13]
                if mac_short not in mac_extra_data_dict:
                    mac_extra_data_dict[mac_short] = list(self._get_device_list_from_query_str(mac_short))
                    logger.info(f'Got MAC List Len: {len(mac_extra_data_dict[mac_short])}')
            except Exception:
                logger.exception(f'Problem getting extra data for {device_raw}')
            data_to_yield = device_raw, mac_extra_data_dict
            yield data_to_yield, CLIENT_TYPE
