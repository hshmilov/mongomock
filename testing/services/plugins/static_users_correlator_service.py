import requests

from services.plugin_service import API_KEY_HEADER, PluginService


class StaticUsersCorrelatorService(PluginService):
    def __init__(self):
        super().__init__('static-users-correlator')

    def correlate(self, blocking: bool):
        response = requests.post(
            self.req_url + f'/trigger/execute?blocking={blocking}',
            headers={API_KEY_HEADER: self.api_key}
        )

        assert response.status_code == 200, \
            f'Error in response: {str(response.status_code)}, ' \
            f'{str(response.content)}'

        return response
