import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from knowbe4_adapter.consts import MAX_NUMBER_OF_DEVICES, DEVICE_PER_PAGE

logger = logging.getLogger(f'axonius.{__name__}')


class Knowbe4Connection(RESTConnection):
    """ rest client for Knowbe4 adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='v1',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._permanent_headers['Authorization'] = f'Bearer {self._apikey}'

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')
        self._get('users', url_params={'page': 1, 'per_page': DEVICE_PER_PAGE})

    def _get_paginated(self, url, url_params=None):
        if not url_params:
            url_params = {}
        page = 1
        url_params['page'] = page
        url_params['per_page'] = DEVICE_PER_PAGE
        resposne = self._get(url, url_params=url_params)
        if not isinstance(resposne, list):
            return
        yield from resposne
        while resposne and (page * DEVICE_PER_PAGE) < MAX_NUMBER_OF_DEVICES:
            try:
                page += 1
                if page % 10 == 1:
                    logger.info(f'Got to page {page}')
                url_params['page'] = page
                url_params['per_page'] = DEVICE_PER_PAGE
                resposne = self._get(url, url_params=url_params)
                if not isinstance(resposne, list):
                    return
                yield from resposne
            except Exception:
                logger.exception(f'Problem with url {url} at page {page}')

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def get_user_list(self):
        sec_test_dict = dict()
        groups_id_dict = dict()
        logger.info(f'Fetching Groups')
        for group_raw in self._get_paginated('groups'):
            if not isinstance(group_raw, dict) or not group_raw.get('id') or not group_raw.get('name'):
                continue
            groups_id_dict[group_raw['id']] = group_raw['name']
        logger.info(f'Fetching Tests')
        pst_count = 0
        for sec_test_raw in self._get_paginated('phishing/security_tests'):
            if pst_count % 10 == 0:
                logger.info(f'Pst count on {pst_count}')
            pst_count += 1
            pst_id = sec_test_raw.get('pst_id')
            try:
                pst_id_data = self._get(f'phishing/security_tests/{pst_id}/recipients')
                for pst_user in pst_id_data:
                    if not pst_user.get('user') or not pst_user['user'].get('id'):
                        continue
                    user_id_for_pst = pst_user['user']['id']
                    if not sec_test_dict.get(user_id_for_pst):
                        sec_test_dict[user_id_for_pst] = []
                    sec_test_dict[user_id_for_pst].append((sec_test_raw, pst_user))
            except Exception:
                logger.exception(f'Problem with pst id {pst_id}')
        logger.info(f'Fetching Enrol')
        enrol_dict = dict()
        for enrol_raw in self._get_paginated('training/enrollments'):
            if not isinstance(enrol_raw, dict) or not enrol_raw.get('user') or not enrol_raw['user'].get('id'):
                continue
            user_id = enrol_raw['user']['id']
            if not enrol_dict.get(user_id):
                enrol_dict[user_id] = []
            enrol_dict[user_id].append(enrol_raw)
        logger.info(f'Fetching users')
        for user_raw in self._get_paginated('users'):
            if not user_raw.get('id'):
                continue
            user_id = user_raw.get('id')
            user_raw['group_names'] = []
            groups_raw = user_raw.get('groups')
            if not isinstance(groups_raw, list):
                groups_raw = []
            for group_id in groups_raw:
                if groups_id_dict.get(group_id):
                    user_raw['group_names'].append(groups_id_dict.get(group_id))
            user_raw['sec_test_user_data'] = sec_test_dict.get(user_id) or []
            user_raw['enrol_data'] = enrol_dict.get(user_id) or []
            yield user_raw

    def get_device_list(self):
        pass
