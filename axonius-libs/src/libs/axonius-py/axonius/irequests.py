import logging

import requests

logger = logging.getLogger(f'axonius.{__name__}')


class IRequests:
    """
    This class is responsible for all internal-networking the system is doing between its own components.
    Any HTTP/S request that is done between internal components of Axonius (e.g. core <-> adapter) should be done
    through here.
    """

    def __init__(self):
        self.session = requests.Session()

    def request(self, method, *args, **kwargs):
        # Set proxies to None, to ignore the environment variables
        if 'proxies' not in kwargs:
            kwargs['proxies'] = {
                'http': None,
                'https': None
            }
        return self.session.request(method, *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.request('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request('post', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.request('put', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.request('delete', *args, **kwargs)

    def head(self, *args, **kwargs):
        return self.request('head', *args, **kwargs)
