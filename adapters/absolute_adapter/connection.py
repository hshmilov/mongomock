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

    # pylint: disable=R0914
    def _create_authorization_header(self, skip):
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
            seconds = '0' + hours
        date_str = (year + month + day).encode('utf-8')
        x_abs_date = year + month + day + 'T' + hours + minute + seconds + 'Z'
        k_date = hmac.new(k_secret, msg=date_str, digestmod=hashlib.sha256).digest()
        k_signing = hmac.new(k_date, msg='abs1_request'.encode('utf-8'), digestmod=hashlib.sha256).digest()
        canonical_request = 'GET' + '\n' + '/v2/reporting/devices' + '\n' + \
                            f'%24skip={skip}&%24top={DEVICE_PER_PAGE}' + '\n' \
                            + f'host:{host}' + '\n' + 'content-type:application/json' + \
                            f'x-abs-date:{x_abs_date}' + \
                            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        hast_temp = hashlib.sha256()
        hast_temp.update(canonical_request.encode('utf-8'))
        hashed_canonical_request = hast_temp.hexdigest()
        credentials_scope = year + month + day + f'/{self._data_center}/abs1'
        string_to_sign = 'ABS1-HMAC-SHA-256' + '\n' + f'{x_abs_date}' + '\n' + f'{credentials_scope}'\
                         + '\n' + f'{hashed_canonical_request}'
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8')).hexdigest()
        self._session_headers['Host'] = host
        self._session_headers['X-abs-date'] = x_abs_date
        self._session_headers['Content-type'] = 'application/json'
        self._session_headers['Authorization'] = f'ABS1-HMAC-SHA-256 Credential={self._token_id}/' \
                                                 f'{credentials_scope}, SignedHeaders = host;content-type;' \
                                                 f'x-abs-date, Signature = {signature}'

    def _connect(self):
        self._create_authorization_header(0)
        self._get('reporting/devices', url_params={'$top': DEVICE_PER_PAGE, '$skip': 0})

    def get_device_list(self):
        skip = 0
        while skip < MAX_NUMBER_OF_DEVICES:
            try:
                self._create_authorization_header(skip)
                devices = self._get('v2/reporting/devices', url_params={'$top': DEVICE_PER_PAGE, '$skip': skip})
                if devices:
                    yield devices
                else:
                    break
                skip += DEVICE_PER_PAGE
            except Exception:
                logger.exception(f'Problem at skip {skip}')
                break
