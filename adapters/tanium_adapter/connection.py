# pylint: disable=invalid-triple-quote, pointless-string-statement
import json
import logging
import time
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from dateutil.tz import tzutc

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from tanium_adapter.consts import MAX_DEVICES_COUNT,\
    CACHE_EXPIRATION, PAGE_SIZE_GET, ENDPOINT_TYPE, PAGE_SIZE_DISCOVER,\
    DISCOVERY_TYPE, SLEEP_GET_RESULT, PAGE_SIZE_GET_RESULT, RETRIES_REFRESH,\
    SLEEP_REFRESH, SLEEP_POLL, SQ_TYPE, STRONG_SENSORS


logger = logging.getLogger(f'axonius.{__name__}')


def listify(x):
    if x is None:
        return []
    if not isinstance(x, (list, tuple)):
        return [x]
    return x


def dt_now():
    return datetime.now(tzutc())


def dt_is_past(value):
    if not isinstance(value, datetime):
        value = parse_date(value)

    return value <= dt_now()


class TaniumConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json, text/plain, */*',
                                  'User-Agent': 'axonius/tanium_adapter'},
                         **kwargs)

    def advanced_connect(self, fetch_discovery, sq_name):
        # NEW: TEST USER HAS PERMISSIONS TO GET system_status
        options = {'row_count': 1, 'row_start': 0}
        self._tanium_get('system_status', options=options)

        # NEW: TEST SQ EXISTS AND USER HAS PERMISSIONS
        if sq_name:
            sq = self._get_by_name(objtype='saved_questions', value=sq_name)
            question = sq.get('question', {})
            selects = question.get('selects', [])
            sensor_names = [x.get('sensor', {}).get('name') for x in selects]
            if 'Computer ID' not in sensor_names:
                raise RESTException('No sensor named “Computer ID” found in Saved Question')
            if not any([x in STRONG_SENSORS for x in sensor_names]):
                found_sensors = ', '.join(sensor_names)
                strong_sensors = ', '.join(STRONG_SENSORS)
                msg = (
                    f'No strong identifier sensor found. Found sensors: {found_sensors}, '
                    f'strong identifier sensors: {strong_sensors}'
                )
                raise RESTException(msg)

        # NEW: TEST DISCOVER EXISTS AND USER HAS PERMISSIONS
        if fetch_discovery:
            body_params = {
                'Id': 'all',
                'Name': 'All Interfaces',
                'Filter': [],
                'Page': {'Size': 1, 'Number': 1},
                'Select': [
                    {'Field': 'Asset.macaddress'},
                    {'Field': 'Asset.computerid'},
                    {'Field': 'Asset.macorganization'},
                    {'Field': 'Asset.hostname'},
                    {'Field': 'Asset.ipaddress'},
                    {'Field': 'Asset.natipaddress'},
                    {'Field': 'Asset.tags'},
                    {'Field': 'Asset.os'},
                    {'Field': 'Asset.osgeneration'},
                    {'Field': 'Asset.ports'},
                    {'Field': 'Asset.method'},
                    {'Field': 'Asset.updatedAt'},
                    {'Field': 'Asset.createdAt'},
                    {'Field': 'Asset.lastManagedAt'},
                    {'Field': 'Asset.lastDiscoveredAt'},
                    {'Field': 'Asset.unmanageable'},
                    {'Field': 'Asset.ismanaged'},
                    {'Field': 'Asset.ignored'},
                ],
                'KeywordFilter': '',
                'CountsOnly': False,
                'ManagementCounts': False,
            }
            self._post('plugin/products/discover/report', body_params=body_params)

    def _connect(self):
        self._test_reachability()
        self._login()

    def _login(self):
        body_params = {'username': self._username, 'password': self._password}
        response = self._post('api/v2/session/login', body_params=body_params)
        if not response.get('data') or not response['data'].get('session'):
            raise RESTException(f'Bad login response: {response}')
        self._session_headers['session'] = response['data']['session']

    def _test_reachability(self):
        # get the tanium version, could be used as connectivity test as it's not an auth/api call
        response = self._get('config/console.json')
        version = response.get('serverVersion')
        if not version:
            raise RESTException(f'Bad server with no version')
        self._platform_version = version
        logger.info(f'Running version: {self._platform_version!r}')

    def _get_endpoints(self):
        """Get all endpoints that have ever registered with Tanium using paging."""
        cache_id = 0
        page = 1
        row_start = 0
        fetched = 0

        while row_start < MAX_DEVICES_COUNT:
            try:
                options = dict()
                options['row_start'] = row_start
                options['row_count'] = PAGE_SIZE_GET
                options['cache_expiration'] = CACHE_EXPIRATION
                if cache_id:
                    options['cache_id'] = cache_id
                data = self._tanium_get('system_status', options=options)

                cache = data.pop()  # cache info should be last item
                data.pop()  # stats entry should be second to last item, we don't need it

                cache_id = cache['cache_id']
                total = cache['cache_row_count']
                fetched += len(data)
                yield from data

                if not data:
                    msg = f'PAGE #{page}: DONE no rows returned'
                    logger.info(msg)
                    break

                if fetched >= total:
                    msg = f'PAGE #{page}: DONE hit rows total'
                    logger.info(msg)
                    break

                row_start += PAGE_SIZE_GET
                page += 1
            except Exception:
                logger.exception(f'Problem in the fetch, row is {row_start}')
                break

    def _tanium_get(self, endpoint, options=None):
        url = 'api/v2/' + endpoint
        response = self._get(url, extra_headers={'tanium-options': json.dumps(options or {})})
        if not response.get('data'):
            raise RESTException(f'Bad response with no data for endpoint {endpoint}')
        return response['data']

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_discovery=False, sq_name=None, sq_refresh=False, sq_max_hours=0):
        for device_raw in self._get_endpoints():
            yield device_raw, ENDPOINT_TYPE
        if fetch_discovery:
            try:
                for device_raw in self._get_discover_assets():
                    yield device_raw, DISCOVERY_TYPE
            except Exception:
                logger.exception(f'Problem fetching discovery')
        if sq_name:
            try:
                for device_raw in self._get_sq_results(name=sq_name,
                                                       refresh=sq_refresh,
                                                       max_hours=sq_max_hours):
                    device_raw, sq_query_text = device_raw
                    data_to_yield = device_raw, sq_name, sq_query_text
                    yield data_to_yield, SQ_TYPE
            except Exception:
                logger.exception(f'Problem getting SQ TYPE')

    def _get_discover_assets(self):
        page = 1
        fetched = 0
        while True:
            try:
                body_params = {
                    'Id': 'all',
                    'Name': 'All Interfaces',
                    'Filter': [],
                    'Page': {'Size': PAGE_SIZE_DISCOVER, 'Number': page},
                    'Select': [
                        {'Field': 'Asset.macaddress'},
                        {'Field': 'Asset.computerid'},
                        {'Field': 'Asset.macorganization'},
                        {'Field': 'Asset.hostname'},
                        {'Field': 'Asset.ipaddress'},
                        {'Field': 'Asset.natipaddress'},
                        {'Field': 'Asset.tags'},
                        {'Field': 'Asset.os'},
                        {'Field': 'Asset.osgeneration'},
                        {'Field': 'Asset.ports'},
                        {'Field': 'Asset.method'},
                        {'Field': 'Asset.updatedAt'},
                        {'Field': 'Asset.createdAt'},
                        {'Field': 'Asset.lastManagedAt'},
                        {'Field': 'Asset.lastDiscoveredAt'},
                        {'Field': 'Asset.unmanageable'},
                        {'Field': 'Asset.ismanaged'},
                        {'Field': 'Asset.ignored'},
                    ],
                    'KeywordFilter': '',
                    'CountsOnly': False,
                    'ManagementCounts': False,
                }

                response = self._post('plugin/products/discover/report', body_params=body_params)
                total = response.get('Total') or 0
                items = response.get('Items')
                columns = response.get('Columns')
                if not items or not isinstance(items, list):
                    logger.error(f'Got bad response with no items: {response}')
                    break
                for item in items:
                    asset = dict(zip(columns, item))
                    yield asset
                this_fetched = len(items)
                fetched += this_fetched

                msg = f'PAGE #{page}: fetched {this_fetched} ({fetched} out of {total} so far) with columns: {columns}'
                logger.info(msg)

                if fetched >= min(total, MAX_DEVICES_COUNT):
                    msg = f'PAGE #{page}: DONE hit rows total'
                    logger.info(msg)
                    break
                page += 1
            except Exception:
                logger.exception(f'Problem with page: {page}')
                break

    def _get_sq_results(self, name, no_results_wait=False, refresh=False, max_hours=0):
        """Get the results from a saved question.

        Args:
            name: Name of the saved question to get results for.
            sleep_poll: Sleep for polling loop for _poll_answers.
            sleep_get_result: Sleep for polling for _get_result_rows.
            refresh: Re-ask the question for the SQ no matter what.
            max_hours: Re-ask the question for the SQ if last asked question is more
                       than this many hours ago.
        """
        # get the SQ object as dict
        saved_question = self._get_by_name(objtype='saved_questions', value=name)

        start = dt_now()
        sq_name = saved_question['name']

        if saved_question.get('question'):
            # SQ was asked before, lets get the details
            question = saved_question['question']
            query = question['query_text']
            expire_dt = parse_date(question['expiration'])
            is_expired = dt_is_past(expire_dt)
        else:
            # SQ has never been asked
            question = None
            query = None
            expire_dt = None
            is_expired = True

        if max_hours and expire_dt:
            # see if question for SQ expiry date is more than max_hours ago
            is_past_max_hours = (start - timedelta(hours=max_hours)) >= expire_dt
        else:
            # either SQ has never been asked, or max_hours is not supplied
            is_past_max_hours = False

        '''
        We only want to refresh if:
          - the question was never asked
          - question is expired (not currently running) and any of:
            - refresh is True
            - max_hours != 0 and start - max_hours >= expire_dt
        '''
        do_refresh = not question or (is_expired and (refresh or is_past_max_hours))

        msg = (
            f'Found saved question {sq_name!r} is_expired: {is_expired}, expire_dt: {expire_dt}'
            f', start: {start}, is_past_max_hours: {is_past_max_hours}, max_hours: {max_hours}'
            f', refresh: {refresh}, do_refresh: {do_refresh}, question: {query!r}'
        )
        logger.info(msg)

        if do_refresh:
            # issue a new question for SQ
            saved_question = self._refresh_sq(saved_question=saved_question)
            question = saved_question['question']

        # wait till either all answers are in for question for SQ
        # or expiry of question for SQ has hit (10 minutes after it was asked)
        self._poll_answers(
            question_id=question['id'], no_results_wait=no_results_wait
        )

        yield from self._get_result_rows(question=question)

    def _poll_answers(self, question_id, no_results_wait=False):
        """Poll a question ID until question expiry or all answers in.

        Question expiry is normally 10 minutes after the question is asked. Expiry means that no more answers
        will come from endpoints, so what has been received so far is all there is.

        Data for a question is normally only available for 5 minutes after expiry,
        unless it's a question asked by a saved question.
        """
        start = dt_now()

        poll_count = 1

        while True:
            question = self._get_by_id(objtype='questions', value=question_id)

            query = question['query_text']
            expire_dt = parse_date(question['expiration'])
            is_expired = dt_is_past(expire_dt)

            endpoint = f'result_info/question/{question_id}'
            datas = self._tanium_get(endpoint=endpoint)
            '''Datas:
            {
                'max_available_age': '0',
                'now': '2019/10/04 16:45:56 GMT-0000',
                'result_infos': [...],
            }
            '''

            data = datas['result_infos'][0]
            '''Data:
            {
                'age': 0,
                'archived_question_id': 0,
                'error_count': 0,
                'estimated_total': 2,
                'expire_seconds': 600,
                'id': 4991,
                'issue_seconds': 300,
                'mr_passed': 2,
                'mr_tested': 2,
                'no_results_count': 0,
                'passed': 2,
                'question_id': 25122,
                'report_count': 2,
                'row_count': 2,
                'row_count_flag': 0,
                'row_count_machines': 2,
                'saved_question_id': 4991,
                'seconds_since_issued': 0,
                'select_count': 2,
                'tested': 2,
            }
            '''

            total = data['estimated_total']
            passed = data['mr_passed']
            has_no_results = data['no_results_count']
            answers_are_in = passed >= total
            time_taken = dt_now() - start

            msg = (
                f'POLL #{poll_count}: Fetched result info for question ID {question_id}, time_taken: {time_taken}'
                f', is_expired: {is_expired}, expire_dt: {expire_dt}'
                f', start: {start}, answers_are_in: {answers_are_in}, info: {data}'
            )
            logger.info(msg)

            if is_expired:
                msg = f'POLL #{poll_count}: DONE question is expired'
                logger.info(msg)
                break

            if answers_are_in:
                if has_no_results and no_results_wait:
                    msg = f'POLL #{poll_count}: WAIT answers are in, but some have ["no results"]'
                    logger.info(msg)
                else:
                    msg = f'POLL #{poll_count}: DONE answers are in'
                    logger.info(msg)
                    break

            poll_count += 1
            time.sleep(SLEEP_POLL)

        return data

    def _refresh_sq(self, saved_question):
        asked_before = bool(saved_question.get('question'))
        sq_name = saved_question['name']
        sq_id = saved_question['id']

        old_id = saved_question.get('question', {}).get('id')
        new_id = None
        tries = 1

        # we don't need the result_info response, its just used to tell the SQ to issue a new question
        endpoint = f'result_info/saved_question/{sq_id}'
        self._tanium_get(endpoint=endpoint)

        # it can take a second for the saved question to update with a new question object after triggering the refresh
        while True:
            if tries > RETRIES_REFRESH:
                msg = (
                    f'No new question issued for {sq_name!r}, asked_before: {asked_before}'
                    f', old_id: {old_id}, new_id: {new_id}, try #{tries}, retries: {RETRIES_REFRESH}'
                )
                logger.info(msg)
                raise RESTException(msg)

            if new_id and (not asked_before or (asked_before and (new_id != old_id))):
                msg = (
                    f'Issued new question for {sq_name!r}, asked_before: {asked_before}'
                    f', old_id: {old_id}, new_id: {new_id}, try #{tries}, retries: {RETRIES_REFRESH}'
                )
                logger.info(msg)
                break

            msg = (
                f'Checking for new question for {sq_name!r}, asked_before: {asked_before}'
                f', old_id: {old_id}, new_id: {new_id}, try #{tries}, retries: {RETRIES_REFRESH}'
            )
            logger.info(msg)

            u_saved_question = self._get_by_id(objtype='saved_questions', value=saved_question['id'])
            new_id = u_saved_question.get('question', {}).get('id')
            tries += 1
            time.sleep(SLEEP_REFRESH)

        return u_saved_question

    def _get_result_rows(self, question, options=None):
        """Get results."""
        endpoint = f'result_data/question/{question["id"]}'

        start = dt_now()

        page = 1
        row_start = 0
        fetched = 0
        columns_map = {}
        cache_id = 0

        while True:
            options = options or {}
            options['row_start'] = row_start
            options['row_count'] = PAGE_SIZE_GET_RESULT
            options['cache_expiration'] = CACHE_EXPIRATION

            if cache_id:
                options['cache_id'] = cache_id

            datas = self._tanium_get(endpoint=endpoint, options=options)
            '''datas:
            {
                'max_available_age': '',
                'now': '2019/10/04 16:32:44 GMT-0000',
                'result_sets': [...]
            }
            '''

            data = datas['result_sets'][0]
            '''data:
            {
              'age': 0,
              'archived_question_id': 0,
              'cache_id': '3232080646',
              'columns': [...],  # columns that can be found in rows, index correlated
              'error_count': 0,
              'estimated_total': 2,  # total number of endpoints currently reporting to tanium
              'expiration': 600,
              'expire_seconds': 0,
              'filtered_row_count': 2,
              'filtered_row_count_machines': 2,
              'id': 25122,
              'issue_seconds': 0,
              'item_count': 2,
              'mr_passed': 2,  # number of systems that have answered the question
              'mr_tested': 2,
              'no_results_count': 0,  # number of systems that have not yet filled in their results (slow sensors)
              'passed': 2,
              'question_id': 25122,
              'report_count': 2,
              'row_count': 2,  # total number of rows in this page
              'row_count_machines': 2,
              'rows': [...]  # rows of data
              'saved_question_id': 0,
              'seconds_since_issued': 0,
              'select_count': 2,
              'tested': 2,
            }
            '''

            columns = data.pop('columns')
            '''columns:
            [
                {'hash': 3409330187, 'name': 'Computer Name', 'type': 1},
                {'hash': 131549066, 'name': 'Online', 'type': 1},
                {'hash': 0, 'name': 'Count', 'type': 3},
            ]
            '''

            rows = data.pop('rows')
            '''rows:
            [
              {
                'cid': 3092775909,
                'data': [
                  [{'text': 'TANIUM-SERVER'}],
                  [{'text': 'True'}],
                  [{'text': '1'}]
                ],
                'id': 2783473000},
              {
                'cid': 15566948,
                'data': [
                  [{'text': 'ip-10-0-2-244'}],
                  [{'text': 'True'}],
                  [{'text': '1'}]
                ],
                'id': 1224714630
              },
            ]
            '''

            cache_id = data['cache_id']
            total = data['estimated_total']
            fetched += len(rows)
            time_taken = dt_now() - start

            msg = (
                f'PAGE #{page}: fetched {fetched} out of {total}'
                f', time_taken: {time_taken} options: {options}, info: {data}'
            )
            logger.info(msg)

            if not columns_map:
                columns_map = self._map_sensors_to_columns(columns=columns)

            for row in rows:
                yield self._get_row_map(row=row, columns_map=columns_map), question.get('query_text')
                '''yield:
                {
                  "Computer Name": {  # Sensor name
                    "Computer Name": [  # Column Name of Sensor
                      "TANIUM-SERVER"  # list of values for column
                    ]
                  },
                  "Online": {
                    "Online": [
                      "True"
                    ]
                  }
                }
                '''

            if not rows:
                msg = f'PAGE #{page}: DONE no rows returned'
                logger.info(msg)
                break

            if fetched >= total:
                msg = f'PAGE #{page}: DONE hit rows total'
                logger.info(msg)
                break

            row_start += PAGE_SIZE_GET_RESULT
            page += 1
            time.sleep(SLEEP_GET_RESULT)

    @staticmethod
    def _get_row_map(row, columns_map):
        """Parse a row of values based on the sensors defined in columns_map."""
        row_map = {}

        if 'cid' in row:
            # this is an odd thing. I've seen cid returned, i've seen it not... shrug
            row_map['Computer ID'] = {'values': row['cid'], 'type': 'String'}

        row_data = row['data']

        if 'Count' in columns_map:
            column_idx, column_info = list(columns_map['Count'].items())[0]
            row_column_values = row_data[column_idx][0]['text']
            '''
            The saved question should have at least one unique identifier
            (name, ID, mac, IP, etc) so that the results come back as one row per endpoint.

            Basically, each row returned from a SQ should ALWAYS have a Count value of 1.

            We log an error and skip the row if Count != 1, otherwise values could
            get correlated to an asset that are actually from multiple assets.
            '''
            if row_column_values not in ['1', 1]:
                msg = f'Count value of {row_column_values!r} is not 1, skipping!'
                logger.error(msg)
                return None

        for sensor_name, columns in columns_map.items():
            if sensor_name == 'Count':
                continue

            if sensor_name not in row_map:
                row_map[sensor_name] = {}

            first_column_idx, first_column_info = list(columns.items())[0]
            first_row_column_values = [x['text'] for x in row_data[first_column_idx]]

            # if not isinstance(first_row_column_values, (tuple, list)):
            #     first_row_column_values = [first_row_column_values]

            if len(columns) == 1:
                # simple single column sensor
                column_name = first_column_info['name']
                column_type = first_column_info['type']
                row_map[column_name] = {'type': column_type, 'value': first_row_column_values}
            else:
                row_column_values = []
                row_map[sensor_name] = {'type': 'object', 'value': row_column_values}

                for row_idx in range(len(first_row_column_values)):
                    row_column_value = {}
                    row_column_values.append(row_column_value)

                    for column_idx, column_info in columns.items():
                        column_name = column_info['name']
                        column_type = column_info['type']
                        row_column_value[column_name] = {
                            'type': column_type,
                            'value': row_data[column_idx][row_idx]['text'],
                        }
        return row_map

    def _map_sensors_to_columns(self, columns):
        """Get a mapping of sensor names to their respective columns returned from results."""
        sensors_by_hash = {}
        sensors_to_columns = {}

        for column_idx, column in enumerate(columns):
            column_name = column['name']
            column_hash = column['hash']

            column_desc = f'Column #{column_idx} named {column_name!r} with sensor hash {column_hash}'

            if column_name == 'Count':
                # Count is an internal column with the number of identical results from endpoints
                sensors_to_columns[column_name] = {column_idx: {'name': column_name, 'type': 'int'}}
                continue

            if column['hash'] not in sensors_by_hash:
                try:
                    # Fetch the sensor object by the hash value for this column.
                    sensor = self._get_by_hash(objtype='sensors', value=column['hash'])
                    sensor_name = sensor['name']

                    # add it to sensor cache so other columns for this sensor don't have to refetch the object
                    sensors_by_hash[column_hash] = sensor

                    msg = f'Fetched uncached sensor {sensor_name!r} for: {column_desc}'
                    logger.info(msg)
                except Exception:
                    # this shouldn't happen
                    msg = f'Failed to fetch sensor for: {column_desc}'
                    logger.exception(msg)
                    raise

                # get subcolumn name and value types defined for this sensor, if any subcolumns defined
                # if subcolumns defined, its an object in axonius
                sensor['column_map'] = {
                    x['name']: x['value_type'] for x in sensor.get('subcolumns', []) or []
                }

                # if no subcolumns defined in sensor, then the only column will be one named after sensor name
                # with the value_type of the sensor itself
                if not sensor['column_map']:
                    sensor['column_map'] = {sensor_name: sensor['value_type']}
            else:
                # We've already fetched the sensor object by hash, get it from our cache
                sensor = sensors_by_hash[column_hash]
                sensor_name = sensor['name']

                msg = f'Found cached sensor {sensor_name!r} for: {column_desc}'
                logger.info(msg)

            if column_name not in sensor['column_map']:
                # this shouldn't happen
                msg = f'Failed to find column in subcolumns {sensor["column_map"]} for: {column_desc}'
                logger.error(msg)
                continue

            if sensor_name not in sensors_to_columns:
                sensors_to_columns[sensor_name] = {}

            sensors_to_columns[sensor_name][column_idx] = {
                'name': column_name, 'type': sensor['column_map'][column_name]
            }

        return sensors_to_columns

    def _get_by_hash(self, objtype: str, value: str) -> dict:
        return self._tanium_get(endpoint=f'{objtype}/by-hash/{value}')

    def _get_by_id(self, objtype: str, value: str) -> dict:
        return self._tanium_get(endpoint=f'{objtype}/{value}')

    def _get_by_name(self, objtype: str, value: str) -> dict:
        return self._tanium_get(endpoint=f'{objtype}/by-name/{value}')
