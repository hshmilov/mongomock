import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class DropboxConnection(RESTConnection):

    def __init__(self, *args, token: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.token = token
        self.headers = None

    def _connect(self):
        if self.token:
            token_type = 'Bearer'
            self._session_headers = {'Authorization': f'{token_type} {self.token}', 'Cache-Control': 'no-cache'}
            try:
                self._post(name='2/team/get_info')
            except Exception:
                logger.exception(f'There was an exception making post request for list member devices')
                raise RESTException('Was unable to get the list of member devices and connect to Dropbox')
        else:
            raise ValueError('Did not provide a session ID')

    def get_device_list(self):
        try:
            team_list_response = self._post(name='2/team/devices/list_members_devices')
            team_list = team_list_response.get('devices', [])
            while team_list_response.get('has_more', False):
                # make authorization header with cursor, and pass in as argument
                cursor = team_list_response.get('cursor', None)
                if cursor:
                    try:
                        updated_body_params = {'cursor': cursor}
                        team_list_response = self._post(
                            name='2/team/devices/list_members_devices', body_params=updated_body_params)
                        team_list.extend(team_list_response.get('devices', []))
                    except Exception:
                        logger.exception('There was an error making subsequent calls to list_member_devices')
                        break

        except Exception:
            logger.exception(f'There was an exception making post request for list member devices')
            raise RESTException('Was unable to get the list of member devices')

        for team in team_list:
            desktop_clients = team.get('desktop_clients', [])
            yield from desktop_clients
            mobile_clients = team.get('mobile_clients', [])
            yield from mobile_clients
