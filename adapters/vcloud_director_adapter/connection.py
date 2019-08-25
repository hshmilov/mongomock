import logging
import math

from collections import OrderedDict

import xmltodict

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import guaranteed_list
from vcloud_director_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class VcloudDirectorConnection(RESTConnection):
    """ rest client for VcloudDirector adapter """

    def __init__(self, *args, **kwargs):
        # Init with version=29.0 which corresponds to vCloud 9.0 (release date 25 Sep 2017)
        super().__init__(
            *args, url_base_prefix='/api', headers={'Accept': 'application/*+xml;version=29.0'}, **kwargs
        )

    def __get_json(self, endpoint: str, url_params: str) -> OrderedDict:
        """
        Gets the endpointand converts the xml response to json
        :param endpoint: the endpoint
        :param url_params: url_params
        :return:
        """
        try:
            xml_response = self._get(
                endpoint,
                url_params=url_params,
                use_json_in_body=False,
                use_json_in_response=False
            )
            return xmltodict.parse(xml_response)
        except Exception as e:
            logger.exception(f'Failed to get endpoint {endpoint}, error is {str(e)}')
            raise

    def __get_json_paginated(self, endpoint: str, url_params: str):
        resp = self.__get_json(endpoint, url_params + f'&page=1&pageSize={consts.DEVICE_PER_PAGE}')
        yield resp

        total_records = False
        if resp.values():
            # We assume that the result lies in the first key in the dict.
            total_records = list(resp.values())[0].get('@total')

        if not total_records:
            return

        total_pages = math.ceil(int(total_records) / consts.DEVICE_PER_PAGE)

        logger.info(f'endpoint "{endpoint}": found {total_records} spreading over {total_pages} pages.')
        for i in range(2, int(total_pages) + 1):
            try:
                yield self.__get_json(endpoint, url_params + f'&page={i}&pageSize={consts.DEVICE_PER_PAGE}')
            except Exception:
                logger.exception(f'Exception while fetching devices at page {i}, breaking')
                break

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        # In case of a success, this sets the session token
        response = self._post(
            'sessions', do_basic_auth=True, use_json_in_body=False, use_json_in_response=False, return_response_raw=True
        )
        if 'x-vcloud-authorization' not in response.headers:
            raise RESTException(f'invalid Response: {response.content}')
        self._session_headers['x-vcloud-authorization'] = response.headers['x-vcloud-authorization']

    # pylint: disable=arguments-differ
    def get_device_list(self, max_async_requsts: int):
        async_requests = []
        for results_page in self.__get_json_paginated(
                'query', 'type=vm&filter=isVAppTemplate==false&format=references'
        ):
            for vm_reference in guaranteed_list((results_page.get('VMReferences') or {}).get('VMReference')):
                if not vm_reference.get('@href'):
                    logger.warning(f'bad vm record {vm_reference}')
                    continue
                async_requests.append(
                    {
                        'name': vm_reference['@href'],
                        'force_full_url': True,
                        'use_json_in_response': False
                    }
                )
        for response in self._async_get_only_good_response(async_requests, chunks=max_async_requsts):
            try:
                yield xmltodict.parse(response)['Vm']
            except Exception:
                logger.exception(f'Could not yield response {response}!')
