import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.cherwell.consts import IT_ASSET_BUS_OB_ID, PAGE_SIZE, MAX_PAGE, INCIDENT_BUS_OB_OD

logger = logging.getLogger(f'axonius.{__name__}')


class CherwellConnection(RESTConnection):
    """ rest client for Cherwell adapter """

    def __init__(self, *args, client_id, **kwargs):
        super().__init__(*args, url_base_prefix='CherwellAPI',
                         headers={'Accept': 'application/json'},
                         **kwargs)
        self._client_id = client_id
        self._last_refresh = None
        self._expires_in = None
        self.__number_of_new_computers = 0
        self.__number_of_new_incidents = 0

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        response = self._post('token',
                              use_json_in_body=False,
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params={'grant_type': 'password',
                                           'client_id': self._client_id,
                                           'username': self._username,
                                           'password': self._password})
        if not isinstance(response, dict) or 'access_token' not in response:
            raise RESTException(f'Bad response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in'])

    def _get_bus_ob_id(self, bus_ob_id_name):
        response = self._get(f'api/V1/getbusinessobjectsummary/busobname/{bus_ob_id_name}')
        if not isinstance(response, list) or not response \
                or not isinstance(response[0], dict) or not response[0].get('busObId'):
            raise RESTException(f'Bad ob id request')
        return response[0].get('busObId')

    def _get_bus_object_template(self, bus_ob_id):
        body_params = {'busObID': bus_ob_id,
                       'includeRequired': 'True',
                       'includeAll': 'True'}
        return self._post('api/V1/GetBusinessObjectTemplate', body_params=body_params)

    def _connect(self):
        if not self._username or not self._password or not self._client_id:
            raise RESTException('No username or password or not Client ID')
        self._refresh_token()
        self._last_refresh = None
        self._expires_in = None

    def _get_bus_ob_id_raw(self, bus_ob_id):
        page = 0
        while page < MAX_PAGE:
            try:
                self._refresh_token()
                response = self._post('api/V1/getsearchresults',
                                      body_params={'busObId': bus_ob_id,
                                                   'searchText': '',
                                                   'pageSize': PAGE_SIZE,
                                                   'pageNumber': page})
                if not response or not isinstance(response, dict) \
                        or not isinstance(response.get('businessObjects'), list):
                    raise RESTException(f'Bad Response: {response}')
                num_busobs = len(response['businessObjects'])
                logger.info(f'Number of bus objs is {num_busobs}')
                yield from response.get('businessObjects')
                if num_busobs < PAGE_SIZE:
                    break
                page += 1
            except Exception:
                logger.exception(f'Problem with page {page}')
                break

    def _get_data_from_ob_rec_id(self, bus_ob_id, bus_ob_rec_id):
        return self._post('api/V1/getbusinessobjectbatch',
                          body_params={'readRequests': [{'busObId': bus_ob_id,
                                                         'busObPublicId': '',
                                                         'busObRecId': bus_ob_rec_id}],
                                       'stopOnError': True})

    def _get_full_data_from_ob_id(self, bus_ob_id):
        for asset_raw in self._get_bus_ob_id_raw(bus_ob_id):
            try:
                bus_ob_id = asset_raw.get('busObId')
                bus_ob_rec_id = asset_raw.get('busObRecId')
                if not bus_ob_id or not bus_ob_rec_id:
                    continue
                self._refresh_token()
                yield self._get_data_from_ob_rec_id(bus_ob_id, bus_ob_rec_id)
            except Exception:
                logger.exception(f'Problem with asset: {asset_raw}')

    def get_device_list(self):
        yield from self._get_full_data_from_ob_id(IT_ASSET_BUS_OB_ID)

    def get_user_list(self):
        yield from self._get_full_data_from_ob_id(self._get_bus_ob_id('Customer'))

    def create_incident(self, cherwell_connection):
        self.__number_of_new_incidents += 1
        logger.info(f'Updating Cherwell computer num {self.__number_of_new_incidents}')
        try:
            bus_ob_id = INCIDENT_BUS_OB_OD
            bus_ob_rec_id = ''
            bus_ob_public_id = ''
            fields_raw = list()
            if cherwell_connection.get('description'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Description',
                                   'name': 'Description',
                                   'fieldId': '252b836fc72c4149915053ca1131d138',
                                   'value': cherwell_connection.get('description')
                                   })
            if cherwell_connection.get('customer_display_name'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Customer Display Name',
                                   'name': 'CustomerDisplayName',
                                   'fieldId': '93734aaff77b19d1fcfd1d4b4aba1b0af895f25788',
                                   'value': cherwell_connection.get('customer_display_name')
                                   })
            if cherwell_connection.get('priority'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Priority',
                                   'name': 'Priority',
                                   'fieldId': '83c36313e97b4e6b9028aff3b401b71c',
                                   'value': cherwell_connection.get('priority')
                                   })
            if cherwell_connection.get('service'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Service',
                                   'name': 'Service',
                                   'fieldId': '936725cd10c735d1dd8c5b4cd4969cb0bd833655f4',
                                   'value': cherwell_connection.get('service')
                                   })
            if cherwell_connection.get('category'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Category',
                                   'name': 'Category',
                                   'fieldId': '9e0b434034e94781ab29598150f388aa',
                                   'value': cherwell_connection.get('category')
                                   })
            if cherwell_connection.get('Source'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Call Source',
                                   'name': 'Source',
                                   'fieldId': '93670bdf8abe2cd1f92b1f490a90c7b7d684222e13',
                                   'value': cherwell_connection.get('Source')
                                   })
            if cherwell_connection.get('subcategory'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Subcategory',
                                   'name': 'Subcategory',
                                   'fieldId': '1163fda7e6a44f40bb94d2b47cc58f46',
                                   'value': cherwell_connection.get('subcategory')
                                   })
            if cherwell_connection.get('incident_type'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Incident Type',
                                   'name': 'IncidentType',
                                   'fieldId': '9365a6098398ff2551e1c14dd398c466d5a201a9c7',
                                   'value': cherwell_connection.get('incident_type')
                                   })
            if cherwell_connection.get('short_description'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Short Description',
                                   'name': 'ShortDescription',
                                   'fieldId': '93e8ea93ff67fd95118255419690a50ef2d56f910c',
                                   'value': cherwell_connection.get('short_description')
                                   })
            if cherwell_connection.get('status'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Status',
                                   'name': 'Status',
                                   'fieldId': '5eb3234ae1344c64a19819eda437f18d',
                                   'value': cherwell_connection.get('status')
                                   })
            body_params = {'busObId': bus_ob_id,
                           'busObRecId': bus_ob_rec_id,
                           'busObPublicId': bus_ob_public_id,
                           'cacheKey': '',
                           'cacheScope': '',
                           'fields': fields_raw,
                           'persist': True}
            device_raw = self._post('api/V1/savebusinessobject',
                                    body_params=body_params)
            return True, device_raw
        except Exception:
            logger.exception(f'Exception while creating incident for '
                             f'num {self.__number_of_new_computers} with connection dict {cherwell_connection}')
            return False, None

    # pylint: disable=too-many-locals, too-many-nested-blocks, too-many-branches, too-many-statements
    def update_cherwell_computer(self, cherwell_connection):
        self.__number_of_new_computers += 1
        logger.info(f'Updating Cherwell computer num {self.__number_of_new_computers}')
        try:
            bus_ob_id = cherwell_connection['bus_ob_id']
            bus_ob_rec_id = cherwell_connection['bus_ob_rec_id']
            bus_ob_public_id = cherwell_connection['bus_ob_public_id']
            fields_raw = list()
            if cherwell_connection.get('name'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Host Name',
                                   'name': 'HostName',
                                   'fieldId': 'BO:9343f882f2b2ae64b1990c41c9bb68410bdbc23528,'
                                              'FI:937905400191ae67dd03ab4b79968fcbaa264b1a75',
                                   'value': cherwell_connection.get('name')
                                   })
                fields_raw.append({'dirty': True,
                                   'displayName': 'Friendly Name',
                                   'name': 'FriendlyName',
                                   'fieldId': 'BO:9343f882f2b2ae64b1990c41c9bb68410bdbc23528,'
                                              'FI:93db94f556e932fd3239504767babd1bfb6c013bb6',
                                   'value': cherwell_connection.get('name')
                                   })
            if cherwell_connection.get('ip_address'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'IP Address',
                                   'name': 'IPAddress',
                                   'fieldId': 'BO:9343f882f2b2ae64b1990c41c9bb68410bdbc23528,'
                                              'FI:9343f943f4c4a38fbe5403469ab01ac8765bb0ae76',
                                   'value': cherwell_connection.get('ip_address')
                                   })
            if cherwell_connection.get('mac_address'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'MAC Address',
                                   'name': 'MACAddress',
                                   'fieldId': 'BO:9343f882f2b2ae64b1990c41c9bb68410bdbc23528,'
                                              'FI:9343f9438810f03daeb78f4be5bf58116ffe5b9dda',
                                   'value': cherwell_connection.get('mac_address')
                                   })
            if cherwell_connection.get('serial_number'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Serial Number',
                                   'name': 'SerialNumber',
                                   'fieldId': 'BO:9343f882f2b2ae64b1990c41c9bb68410bdbc23528,'
                                              'FI:9343f88b85daf1bc3c475541a48526fdec9dc25960',
                                   'value': cherwell_connection.get('serial_number')
                                   })
            if cherwell_connection.get('os'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Operating System',
                                   'name': 'OperatingSystem',
                                   'fieldId': 'BO:9343f882f2b2ae64b1990c41c9bb68410bdbc23528,'
                                              'FI:93790597a2bebf214063ac4f8096aa5e3ead9b3da5',
                                   'value': cherwell_connection.get('os')
                                   })
            if cherwell_connection.get('os_build'):
                fields_raw.append({'dirty': True,
                                   'displayName': 'Operating System Version',
                                   'name': 'OperatingSystemVersion',
                                   'fieldId': 'BO:9343f882f2b2ae64b1990c41c9bb68410bdbc23528,'
                                              'FI:937905992a654f534d3a794e72bd89ba330c0790f8',
                                   'value': cherwell_connection.get('os_build')
                                   })
            if cherwell_connection.get('extra_fields'):
                try:
                    extended_fields_dict = dict()
                    extra_fields = cherwell_connection.get('extra_fields')
                    template = self._get_bus_object_template(bus_ob_id)
                    for field_data in template['fields']:
                        if not field_data.get('name'):
                            continue
                        extended_fields_dict[field_data['name']] = (field_data.get('fieldId'),
                                                                    field_data.get('displayName'))
                    for key, value in extra_fields.items():
                        try:
                            if not extended_fields_dict.get(key):
                                continue
                            field_id, display_name = extended_fields_dict.get(key)
                            fields_raw.append({'value': value,
                                               'name': key,
                                               'displayName': display_name,
                                               'dirty': True,
                                               'fieldId': field_id})
                        except Exception:
                            logging.exception(f'Problem with key {key}')
                except Exception:
                    logging.exception(f'Problem with extra fields')
            body_params = {'busObId': bus_ob_id,
                           'busObRecId': bus_ob_rec_id,
                           'busObPublicId': bus_ob_public_id,
                           'cacheKey': '',
                           'cacheScope': '',
                           'fields': fields_raw,
                           'persist': True}
            device_raw = self._post('api/V1/savebusinessobject',
                                    body_params=body_params)
            asset_response = None
            try:
                bus_ob_public_id = device_raw.get('busObPublicId')
                asset_response = self._post('api/V1/getbusinessobjectbatch',
                                            body_params={'readRequests': [{'busObId': bus_ob_id,
                                                                           'busObPublicId': bus_ob_public_id,
                                                                           'busObRecId': device_raw.get('busObRecId')}],
                                                         'stopOnError': True})
            except Exception:
                logger.exception(f'Problem refreshing device {device_raw}')
            return True, asset_response
        except Exception:
            logger.exception(f'Exception while creating computer for '
                             f'num {self.__number_of_new_computers} with connection dict {cherwell_connection}')
            return False, None
