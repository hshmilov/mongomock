# pylint: disable=import-error
import hmac
import hashlib
import logging
import datetime
from urllib3.util.url import parse_url

from axonius.clients.rest.connection import RESTConnection
from absolute_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class AbsoluteConnection(RESTConnection):
    """ rest client for Absolute adapter """

    def __init__(self, *args, token_id, client_secret, data_center, **kwargs):
        super().__init__(*args, **kwargs)
        self._token_id = token_id
        self._client_secret = client_secret
        self._data_center = data_center.lower()

    def _create_authorization_header_for_url(self, url, skip):
        self._create_authorization_header(url=url,
                                          url_params=f'%24skip={skip}&%24top={DEVICE_PER_PAGE}')

    # pylint: disable=R0914
    def _create_authorization_header(self, url, url_params):
        k_secret = ('ABS1' + self._client_secret).encode('utf-8')
        host = parse_url(self._domain).host
        now = datetime.datetime.utcnow()
        year = str(now.year)
        day = str(now.day)
        if len(day) == 1:
            day = '0' + day
        month = str(now.month)
        if len(month) == 1:
            month = '0' + month
        hours = str(now.hour)
        if len(hours) == 1:
            hours = '0' + hours
        minute = str(now.minute)
        if len(minute) == 1:
            minute = '0' + minute
        seconds = str(now.second)
        if len(seconds) == 1:
            seconds = '0' + seconds
        date_str = (year + month + day).encode('utf-8')
        x_abs_date = year + month + day + 'T' + hours + minute + seconds + 'Z'
        k_date = hmac.new(k_secret, msg=date_str, digestmod=hashlib.sha256).digest()
        k_signing = hmac.new(k_date, msg='abs1_request'.encode('utf-8'), digestmod=hashlib.sha256).digest()
        canonical_request = 'GET' + '\n' + url + '\n' + \
                            url_params + '\n' \
                            + f'host:{host}' + '\n' + 'content-type:application/json' + '\n' +\
                            f'x-abs-date:{x_abs_date}' + '\n' + \
                            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        hast_temp = hashlib.sha256()
        hast_temp.update(canonical_request.encode('utf-8'))
        hashed_canonical_request = hast_temp.hexdigest()
        credentials_scope = year + month + day + f'/{self._data_center}/abs1'
        string_to_sign = 'ABS1-HMAC-SHA-256' + '\n' + f'{x_abs_date}' + '\n' + f'{credentials_scope}'\
                         + '\n' + f'{hashed_canonical_request}'
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
        self._session_headers['Host'] = host
        self._session_headers['X-Abs-Date'] = x_abs_date
        self._session_headers['Content-Type'] = 'application/json'
        self._session_headers['Authorization'] = f'ABS1-HMAC-SHA-256 Credential={self._token_id}/' \
            f'{credentials_scope}, SignedHeaders=host;content-type;' \
            f'x-abs-date, Signature={signature}'

    def _connect(self):
        self._create_authorization_header_for_url('/v2/reporting/devices', 0)
        self._get('v2/reporting/devices', url_params={'$skip': 0, '$top': DEVICE_PER_PAGE})

    def _get_endpoint(self, url):
        skip = 0
        while skip < MAX_NUMBER_OF_DEVICES:
            try:
                self._create_authorization_header_for_url(f'/{url}', skip)
                devices = self._get(url, url_params={'$skip': skip, '$top': DEVICE_PER_PAGE})
                if devices:
                    for i, device_raw in enumerate(devices):
                        logger.debug(f'Got to index {i}')
                        yield device_raw
                else:
                    break
                skip += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at skip {skip}')
                break

    # pylint: disable=too-many-locals, too-many-nested-blocks, too-many-branches, arguments-differ
    def get_device_list(self, fetch_cdf=False, fetch_apps=False):
        apps_to_device_dict = dict()
        if fetch_apps:
            for app_raw in self._get_endpoint('v2/sw/deviceapplications'):
                try:
                    device_id = app_raw.get('deviceUid')
                    if not device_id:
                        continue
                    if device_id not in apps_to_device_dict:
                        apps_to_device_dict[device_id] = []
                    apps_to_device_dict[device_id].append(app_raw)
                except Exception:
                    logger.exception(f'Problem with app {app_raw}')

        for device_raw in self._get_endpoint('v2/reporting/devices'):
            try:
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device_raw['apps_raw'] = apps_to_device_dict.get(device_id)
                if fetch_cdf:
                    self._create_authorization_header(url=f'/v2/reporting/devices/{device_id}/cfd',
                                                      url_params='')
                    device_raw['cfd_fields'] = self._get(f'v2/reporting/devices/{device_id}/cfd')
            except Exception:
                logger.debug(f'Problem getting fields', exc_info=True)
            yield device_raw
