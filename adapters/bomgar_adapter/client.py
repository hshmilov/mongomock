import datetime
import json
from gzip import decompress as gzip_decompress
import requests
import xml.etree.cElementTree as ET

from bomgar_adapter.exceptions import BomgarAlreadyConnected, BomgarConnectionError, BomgarNotConnected, \
    BomgarRequestException
from bomgar_adapter.json_utils import xml2json


class BomgarConnection(object):
    """ for details see https://axonius.atlassian.net/wiki/spaces/AX/pages/509706241/Bomgar """

    def __init__(self, domain, client_id, client_secret):
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret

        url = domain
        if not url.lower().startswith('https://'):
            url = f'https://{url}'
        if not url.endswith('/'):
            url += '/'
        self.oauth2_url = f'{url}oauth2/token'
        self.command_url = f'{url}api/command?action='
        self.report_url = f'{url}api/reporting'

        self.token = None
        self.session = None
        self.headers = None

    def set_token(self, token, token_type='Bearer'):
        if token_type is None:
            token_type = 'Bearer'
        self.token = token
        self.headers = {'Authorization': f'{token_type} {self.token}'}

    @property
    def is_connected(self):
        return self.session is not None

    def __del__(self):
        if hasattr(self, 'session') and self.is_connected:
            self.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()

    def _get_url_command(self, action):
        return self.command_url + action

    def close(self):
        self.session.close()
        self.session = None
        self.token = None

    def connect(self):
        if self.is_connected:
            raise BomgarAlreadyConnected()
        session = requests.Session()
        response = session.post(self.oauth2_url, data={'grant_type': 'client_credentials'}, auth=(self.client_id,
                                                                                                  self.client_secret))
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise BomgarConnectionError(str(e))
        response = response.json()
        if 'access_token' not in response:
            error = response.get('error', 'unknown connection error')
            message = response.get('message', '')
            if message:
                error += ': ' + message
            raise BomgarConnectionError(error)
        self.set_token(response['access_token'], response.get('token_type'))
        self.session = session

    def _get(self, action, params=None, command=True, is_text=True):
        if not self.is_connected:
            raise BomgarNotConnected()
        params = params or {}
        url = self._get_url_command(action) if command else self.report_url
        response = self.session.get(url, params=params, headers=self.headers, stream=True)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise BomgarRequestException(str(e))
        if not is_text:
            return response.raw
        data = response.content.decode('utf-8')
        if command:
            data = data.replace('xmlns="http://www.bomgar.com/namespaces/API/command"', '')
        else:
            data = data.replace('xmlns="http://www.bomgar.com/namespaces/API/reporting"', '')
        return data

    def get_appliances(self):
        return self._get('get_appliances')

    def get_api_info(self):
        return self._get('get_api_info')

    def get_connected_client_list(self, client_type='all', summary_only=False):
        """ returns details of all connected Bomgar clients """
        assert client_type in ('all', 'representative', 'support_customer', 'presentation_attendee', 'push_agent')
        params = {'type': client_type, 'summary_only': int(summary_only)}
        return self._get('get_connected_client_list', params)

    def get_connected_clients(self, client_id=None, client_type='all', include_connections=False):
        """ returns details of all connected Bomgar clients """
        assert client_type in ('all', 'representative', 'support_customer', 'presentation_attendee', 'push_agent')
        params = {'type': client_type, 'include_connections': int(include_connections)}
        if client_id is not None:
            if isinstance(client_id, (list, tuple)):
                client_id = ','.join(client_id)
            assert isinstance(client_id, str)
            assert len(client_id.split(',')) < 100  # as mentioned in the docs
            params['id'] = client_id
        return self._get('get_connected_clients', params)

    def get_archive_listing(self, date):
        report = self._get('', {'generate_report': 'ArchiveListing', 'date': date}, command=False)
        xml = ET.fromstring(report)
        archives = []
        for item in xml.getchildren():
            value = xml2json(item)[item.tag]
            value['archive_type'] = item.tag
            if item.tag == 'event_archive':
                archives.append(value)
            elif item.tag == 'state_archive':
                archives.append(value)
            else:
                assert False
        return archives

    def get_archive(self, date, index, archive_type):
        assert archive_type in ('event', 'state')
        report = self._get('', {'generate_report': 'Archive', 'date': date, 'type': 'state', 'index': index},
                           command=False, is_text=False)
        data = gzip_decompress(report.read()).decode('utf-8')
        if data == '<?xml version="1.0" encoding="UTF-8"?>\n\n<error xmlns="http://www.bomgar.com/namespaces/API/reporting">No archives found for the given search criteria.</error>\n\n\n\n':
            return None
        return json.loads(data)

    def get_clients_history(self, max_history_days=7):
        assert isinstance(max_history_days, int) and 1 <= max_history_days <= 7
        # We first acquire the current timestamp on bomgar server.
        timestamp = int(ET.fromstring(self.get_api_info()).find('timestamp').text)
        last_timestamp = datetime.datetime.fromtimestamp(timestamp)

        one_day = datetime.timedelta(days=1)
        possible_client_types = ('customer_client', 'representative')
        all_clients = {}
        client_sessions = {}

        # now we iterate *forwards* in the history (up to maximum available of 7 days)
        for day in range(max_history_days):
            current_timestamp = last_timestamp - (((max_history_days - 1) - day) * one_day)
            date = f'{current_timestamp.year}-{current_timestamp.month:02}-{current_timestamp.day:02}'

            # Get the listing of available archives on that date
            archives = self.get_archive_listing(date)

            # for each listing we retrieve the archive itself
            for archive_listing in archives:
                if archive_listing['archive_type'] == 'event_archive':
                    archive = self.get_archive(date, archive_listing['index'], 'event')
                    listing_timestamp = int(archive_listing['start_time']['@timestamp'])
                elif archive_listing['archive_type'] == 'state_archive':
                    archive = self.get_archive(date, archive_listing['index'], 'state')
                    listing_timestamp = int(archive_listing['time']['@timestamp'])
                else:
                    assert False
                if archive is None:
                    continue

                # we only care about two "tables" in the returned "db"
                for client_type in possible_client_types:
                    clients = archive.get(client_type)
                    if clients is None or len(clients) == 0:
                        continue

                    # we save each client under its "key" (in Bomgar's case its the hostname)
                    for client in clients.values():
                        hostname = client['hostname']
                        client_dict = {
                            'device_type': client_type,
                            'hostname': hostname,
                            'operating_system': client['operating_system'],
                            'private_ip': client['private_ip'],
                            'public_ip': client['public_ip'].split(':', 1)[0],
                            'created_timestamp': client['created_timestamp'],
                            'last_seen': listing_timestamp
                        }

                        if client_type == 'representative':
                            for key in ('public_display_name', 'user_id', 'username'):
                                client_dict[key] = client[key]

                        all_clients[hostname] = client_dict

                # extract the last support session and set the 'last_session' fields for each client.
                support_sessions = archive['support_session']
                if support_sessions is not None:
                    for support_session_id, support_session in support_sessions.items():
                        hostname = support_session['customer_name']
                        session = {
                            'last_session_start': support_session['created_timestamp'],
                            'last_session_start_method': support_session['start_method'],
                        }
                        last_session_representative_username = None
                        # get the representative username by support_session_id
                        for representative_support_session in archive['representative_support_session'].values():
                            if representative_support_session['support_session_id'] == support_session_id:
                                representative_id = representative_support_session['representative_id']
                                last_session_representative_username = archive['representative'].get(representative_id,
                                                                                                     {}).get('username')
                                break
                        if last_session_representative_username is not None:
                            session['last_session_representative_username'] = last_session_representative_username
                        client_sessions[hostname] = session

        # set the last_session info for each available client
        for hostname, session in client_sessions.items():
            if hostname not in all_clients:
                continue
            all_clients[hostname].update(session)
        return all_clients
