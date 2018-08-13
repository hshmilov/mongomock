#!/usr/bin/env python3


import asyncio
import copy
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

import requests

import aiohttp
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils import json

logger = logging.getLogger(f'axonius.{__name__}')


class RedSealException(Exception):
    pass


class RedSealClient:
    def __init__(self, url, username, password):
        if not urlparse(url).scheme:
            # Set default scheme to https
            url = 'https://' + url
        self._url = url
        self._username = username
        self._password = password

    async def get(self, session, path, *args, headers=None, **kwargs):
        """
        Wrapper for invoking async session get
        Disables ssl verify, adds url and creds.
        add accpet json header to tell the server that we want json
        """
        try:
            if headers is None:
                headers = {}

            headers['Accept'] = 'application/json'

            url = urljoin(self._url + '/', path)
            logger.debug(f'getting {url}')

            async with session.get(url, headers=headers, auth=aiohttp.BasicAuth(self._username, self._password),
                                   *args, verify_ssl=False, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except Exception:
            logger.warning('exception while handling respones')

    def check_connection(self):
        """
        Validate that we can open session using the given creds.
        """

        logger.info(f'Creating session using {self._username}')
        try:

            response = requests.get(urljoin(self._url + '/', 'data'),
                                    auth=(self._username, self._password), verify=False, timeout=10)
            response.raise_for_status()
        except Exception as exc:
            exception_data = response.content if 'response' in locals() else ''
            logger.exception(f'Exception in check connection response: {exception_data}')
            raise ClientConnectionException(f'Error connecting to server: {str(exc)}')

    @staticmethod
    def reassemble_application_json(response):
        """
        In redseal rest api, list with one object == the object,
        so we must first fix this bug inorder to parse the json
        """
        response = copy.deepcopy(response)
        if 'list' not in response:
            raise RedSealException('Missing list field in application json')

        for key, value in response['list'][0].items():
            if isinstance(value, dict):
                # list with length == 1 found - fix it
                response['list'][0][key] = [value, ]
        return response

# pylint: disable=R0912
# This function has too many branches becuse redseal json is wierd
    @staticmethod
    def reassemble_device_json(response):
        """
        In redseal rest api, list with one object == the object,
        so we must first fix this bug inorder to parse the json
        We dont want to raise exception when field is missing - we only want to fix broken fields
        """
        response = copy.deepcopy(response)
        data = list(response.values())[0]

        if 'Interfaces' in data:
            if isinstance(data['Interfaces'], dict):
                data['Interfaces'] = [data['Interfaces'], ]

            for interface in data['Interfaces']:
                if 'Interface' not in interface:
                    logger.warning('Missing Interface field')
                    continue

                if isinstance(interface['Interface'], dict):
                    interface['Interface'] = [interface['Interface'], ]
        else:
            logging.warning('Missing Interfaces field in response')

        if 'Applications' in data:
            if isinstance(data['Applications'], dict):
                data['Applications'] = [data['Applications'], ]

            for application in data['Applications']:
                if 'Application' not in application:
                    logger.warning('Missing Application field')
                    continue

                if isinstance(application['Application'], dict):
                    application['Application'] = [application['Application'], ]

                for app in application['Application']:
                    if 'Vulnerabilities' not in app:
                        # dont do logger.info this is going to happen alot
                        logger.debug(f'No Vulnerabilities in {app}')
                        continue

                    if isinstance(app['Vulnerabilities'], dict):
                        app['Vulnerabilities'] = [app['Vulnerabilities'], ]

                    for vulnerability in app['Vulnerabilities']:
                        if 'Vulnerability' not in vulnerability:
                            logger.warning(f'no Vulnerability in {vulnerability}')
                            continue

                        if isinstance(vulnerability['Vulnerability'], dict):
                            vulnerability['Vulnerability'] = [vulnerability['Vulnerability'], ]
        else:
            logging.warning('Missing Applications in response')
        return response

    @staticmethod
    def get_urls(response):
        for key, value in response['list'][0].items():
            logging.debug(f'handling {key}')
            for tree in value:
                if 'URL' not in tree:
                    logger.error(f'tree {tree} is missing "url"')
                    continue
                yield tree['URL']

    async def _get_devices(self, loop):
        pool = ThreadPoolExecutor(10)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            response = await self.get(session, 'data/application/*')
            if not json.is_valid(response, {'list': ['Host', ]}):
                raise RedSealException('Invalid response for /data/host/full')

            response = self.reassemble_application_json(response)

            results = []
            urls = self.get_urls(response)
            tasks = map(lambda url: loop.create_task(self.get(session, url)), urls)

            for future in asyncio.as_completed(tasks):
                try:
                    result = await loop.run_in_executor(pool, self.reassemble_device_json, await future)
                    if result is not None:
                        results.append(result)
                except Exception:
                    logging.exception('Exception while handling device')

        return results

    def get_devices(self):
        """
        Get device list using RedSeal API.
        Requires active session.
        :return: json that contains a list of the devices
        """

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            devices = loop.run_until_complete(self._get_devices(loop))
        finally:
            # Wait for connection close (took from aiohttp manual)
            loop.run_until_complete(asyncio.sleep(0.250))

        return devices
