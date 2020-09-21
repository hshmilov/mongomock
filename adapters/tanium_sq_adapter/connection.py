import datetime
import json
import logging
import time

from axonius.clients import tanium
from axonius.clients.rest.connection import RESTException
from tanium_sq_adapter.consts import (
    CACHE_EXPIRATION,
    CID_SENSOR,
    HEADERS,
    MAX_DEVICES_COUNT,
    MAX_HOURS,
    NET_SENSOR_DISCOVER,
    NET_SENSORS,
    NO_RESULTS_WAIT,
    PAGE_SIZE,
    REASK_RETRIES,
    REASK_SLEEP,
    REFRESH,
    REQUIRED_SENSORS,
    SLEEP_GET_ANSWERS,
    SLEEP_POLL_ANSWERS,
)

# pylint: disable=too-many-locals,C0330

logger = logging.getLogger(f'axonius.{__name__}')


def kvdump(value, sort=True):
    value = sorted(value.items()) if sort else value.items()
    return ', '.join([f'{k}={v}' for k, v in value])


def sq_info(sq_obj):
    return f'sq_name={sq_obj["name"]!r}, sq_id={sq_obj["id"]}, qid={get_qid(sq_obj)}'


def get_qid(sq_obj):
    return (sq_obj.get('question', {}) or {}).get('id')


def get_expiry(sq_obj):
    src = sq_info(sq_obj)
    q_obj = sq_obj['question']
    # question:
    # The question from which to create the saved question.

    expiration = q_obj['expiration']
    # expiration:
    # The date and time when the question expires. Format is yyyy-mm-ddThh:mm:ss. For example, 2012-07-24T12:31:00.

    expired_dt = tanium.tools.parse_dt(value=expiration, src=src)

    value = {}
    value['expired_dt'] = expired_dt
    value['expired_minutes_ago'] = tanium.tools.dt_calc_mins(value=expired_dt, reverse=False, src=src)
    value['minutes_till_expired'] = tanium.tools.dt_calc_mins(value=expired_dt, reverse=True, src=src)
    value['is_expired'] = tanium.tools.dt_is_past(value=expired_dt, src=src)

    logger.info(f'{src} [EXPIRY] {kvdump(value)}')
    return value


def json_dump(obj):
    return json.dumps(obj, indent=2)


class TaniumSqConnection(tanium.connection.TaniumConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='', headers=HEADERS, **kwargs)

    def advanced_connect(self, client_config):
        for name in self._sq_names(sq_names=client_config['sq_name']):
            self._get_sq(name=name)

    @property
    def module_name(self):
        return 'interact'

    @staticmethod
    def _sq_names(sq_names):
        return [x.strip() for x in sq_names.split(',') if x.strip()]

    # pylint: disable=arguments-differ
    def get_device_list(self, client_name, client_config, page_sleep=SLEEP_GET_ANSWERS, page_size=PAGE_SIZE):
        server_version = self._get_version()
        workbenches = self._get_workbenches_meta()

        metadata = {
            'server_name': client_config['domain'],
            'client_name': client_name,
            'server_version': server_version,
            'workbenches': workbenches,
        }

        sqargs = {
            'refresh': client_config.get('sq_refresh', REFRESH),
            'max_hours': client_config.get('sq_max_hours', MAX_HOURS),
            'no_results_wait': client_config.get('no_results_wait', NO_RESULTS_WAIT),
            'page_sleep': page_sleep,
            'page_size': page_sleep,
        }
        try:
            for name in self._sq_names(sq_names=client_config['sq_name']):
                for device_raw in self._get_sq_results(name=name, **sqargs):
                    sq_device_raw, sq_query_text = device_raw
                    data_to_yield = sq_device_raw, name, sq_query_text
                    yield data_to_yield, metadata
        except Exception as exc:
            raise RESTException(f'Problem fetching Saved Question assets for {name!r}: {exc}')

    @staticmethod
    def missing_sensors(name, sensor_names):
        missing_requireds = [x for x in REQUIRED_SENSORS if x not in sensor_names]

        if missing_requireds:
            found = ', '.join(sensor_names)
            req = ', '.join(REQUIRED_SENSORS)
            miss = ', '.join(missing_requireds)
            msg = '\n -- '.join(
                [
                    f'Saved Question {name!r}',
                    f'MISSING REQUIRED SENSORS: {miss}',
                    f'SENSORS REQUIRED: {req}',
                    f'SENSORS FOUND: {found}',
                ]
            )
            return msg

        has_network_discover = NET_SENSOR_DISCOVER in sensor_names
        has_network_base = all([x in sensor_names for x in NET_SENSORS])
        has_network = any([has_network_discover, has_network_base])

        if not has_network:
            found = ', '.join(sensor_names)

            network_base = ' AND '.join(NET_SENSORS)
            msg = '\n -- '.join(
                [
                    f'Saved Question {name!r}',
                    f'MISSING REQUIRED NETWORK SENSORS: {NET_SENSOR_DISCOVER} or {network_base}',
                    f'ALL SENSORS FOUND: {found}',
                ]
            )
            return msg

        return None

    def _get_sq(self, name):
        sq = self._get_by_name(objtype='saved_questions', value=name)
        question = sq.get('question', {})
        selects = question.get('selects', [])
        sensor_names = [x.get('sensor', {}).get('name') for x in selects]

        missing = self.missing_sensors(name=name, sensor_names=sensor_names)
        if missing:
            raise RESTException(missing)
        return sq

    def _tanium_get(self, endpoint, options=None, return_obj=False, **kwargs):
        def pre():
            return f'ERROR: HTTP GET {url!r} code {code}: '

        url = 'api/v2/' + endpoint
        get_url = f'{self._url}/{url}'

        headers = {'tanium-options': json.dumps(options or {})}
        response = self._get(
            get_url, extra_headers=headers, raise_for_status=False, return_response_raw=True, use_json_in_response=False
        )
        code = response.status_code

        obj = {}

        if response.text:
            try:
                obj = response.json()
            except Exception as exc:
                msg = f'{pre()}JSON error {exc}, body: {response.text}'
                logger.exception(msg)
                response.raise_for_status()
                raise RESTException(msg)

        if not obj:
            raise RESTException(f'{pre()}No object returned, body: {response.text}')

        if obj and return_obj:
            return obj

        obj_keys = list(obj)
        text = obj.pop('text', '')
        data = obj.pop('data', {})
        obj_text = kvdump(obj) if obj else ''

        if text:
            text = ', '.join([x.strip() for x in text.splitlines() if x.strip()])
            raise RESTException(f'{pre()}{text} {obj_text}')

        if not data:
            raise RESTException(f'{pre}No data key in {obj_keys}, {obj_text}, body: {response.text}')

        response.raise_for_status()

        return data

    def _get_q(self, qid):
        q_obj = self._get_by_id(objtype='questions', value=qid)
        return q_obj

    def _refetch_sq(self, sq_obj):
        return self._get_by_id(objtype='saved_questions', value=sq_obj['id'])

    def _get_result_data_q(self, qid, **kwargs):
        datas = self._tanium_get(endpoint=f'result_data/question/{qid}', **kwargs)
        return datas

    def _get_result_info_q(self, qid, **kwargs):
        datas = self._tanium_get(endpoint=f'result_info/question/{qid}', **kwargs)
        return datas

    def _get_result_data_sq(self, sq_id, **kwargs):
        datas = self._tanium_get(endpoint=f'result_data/saved_question/{sq_id}', **kwargs)
        return datas

    def _rbac_gri_ok(self, qid, **kwargs):
        """Check RBAC access is ok for get result info on a question ID.

        1. If an Administrator opens a Saved Question for editing in the GUI, a Question for that Saved Question
           will be asked by the GUI. The results for this question can only be accessed by Administrators, so a limited
           privilege user will get a 403 error when trying to get results for this question. This will keep
           happening as long as the Administrator has the Saved Question open for edit in the GUI.

        2. If a user changes the "Visibility" setting for a Saved Question in the GUI to
           "Only the Owner and Admins can see this object", a limited privilege user will get a 403
           error for all Questions that get asked for that Saved Question. If the "Visibility" setting for that
           Saved Question is changed to "According to RBAC", the Question that was last asked for that
           Saved Question will still be inaccessible to a limited privilege user.
        """

        def pre():
            return f'qid={qid} [RBAC GRI OK] '

        ri_obj = self._get_result_info_q(qid=qid, return_obj=True)
        text = ri_obj.get('text') or ''
        logger.debug(f'{pre()}question result info {json_dump(ri_obj)}')

        if text:
            text = ' '.join([x.strip() for x in text.splitlines() if x.strip()])
            logger.info(f'{pre()}ERROR for get result info on qid={qid}: {text}')
            return False

        logger.info(f'{pre()}SUCCESS for get result info on qid={qid}')
        return True

    def _get_result_info_sq(self, sq_id, **kwargs):
        def stats():
            value = [
                f'attempt #{attempts}/{max_attempts}',
                f'sleep={sleep}',
                f'sq_id={sq_id}',
            ]
            return ', '.join(value)

        def pre():
            return f'sq_id={sq_id} [SQ GRI] '

        # doing a get result info on a SQ causes a new question to be asked for that SQ
        attempts = 0
        max_attempts = 5
        sleep = 5

        while True:
            ri_obj = self._tanium_get(endpoint=f'result_info/saved_question/{sq_id}', return_obj=True)
            text = ri_obj.get('text') or ''
            data = ri_obj.get('data') or ''

            if not text and data:
                return data

            logger.debug(f'{pre()}SQ result info {stats()}\n{json_dump(ri_obj)}')

            text = ' '.join([x.strip() for x in text.splitlines() if x.strip()])
            msg = f'{pre()}ERROR: {text} {stats()}'
            logger.error(msg)

            if attempts > max_attempts:
                raise RESTException(msg)

            attempts += 1
            time.sleep(sleep)

    def _get_sq_results(
        self,
        name,
        no_results_wait=NO_RESULTS_WAIT,
        refresh=REFRESH,
        max_hours=MAX_HOURS,
        page_size=PAGE_SIZE,
        page_sleep=SLEEP_GET_ANSWERS,
    ):
        """Get the results from a saved question."""

        def pre():
            return f'{sq_info(sq_obj)} [GET_SQ_RESULTS] '

        sq_obj = self._get_sq(name=name)
        sq_obj = self._reask_check(sq_obj=sq_obj, refresh=refresh, max_hours=max_hours)

        query = sq_obj['question']['query_text']
        logger.info(f'{pre()}query: {query}')

        if get_expiry(sq_obj=sq_obj)['is_expired']:
            logger.info(f'{pre()}question is expired, not polling for answers')
        else:
            if no_results_wait:
                logger.info(f'{pre()}question is not expired, waiting for expiry')
                sq_obj = self._wait_for_expiry(sq_obj=sq_obj)
            else:
                # wait till either all answers are in for question for SQ
                # or expiry of question for SQ has hit (10 minutes after it was asked)
                logger.info(f'{pre()}question is not expired, polling for answers')
                sq_obj = self._poll_answers(sq_obj=sq_obj)

        logger.info(f'{pre()}getting answers')
        yield from self._get_answers(sq_obj=sq_obj, page_size=page_size, page_sleep=page_sleep)

    def _reask_check(self, sq_obj, refresh=REFRESH, max_hours=MAX_HOURS):
        def pre():
            return f'{sq_info(sq_obj)} [REASK CHECK] '

        q_obj = sq_obj.get('question')

        if not q_obj:
            logger.info(f'{pre()}RE-ASKING, question never asked before')
            return self._reask_do(sq_obj=sq_obj)

        if not self._rbac_gri_ok(qid=get_qid(sq_obj=sq_obj)):
            logger.info(f'{pre()}RE-ASKING, RBAC denied access')
            return self._reask_do(sq_obj=sq_obj)

        if max_hours:
            expiry = get_expiry(sq_obj=sq_obj)
            then = tanium.tools.dt_now() - datetime.timedelta(hours=max_hours)
            is_past_max_hours = then > expiry['expired_dt']
            if is_past_max_hours:
                logger.info(f'{pre()}RE-ASKING, question is expired and is past max hours {max_hours}')
                return self._reask_do(sq_obj=sq_obj)

        if refresh:
            logger.info(f'{pre()}RE-ASKING, question is expired and refresh={refresh}')
            return self._reask_do(sq_obj=sq_obj)

        logger.info(f'{pre()}NOT RE-ASKING, no refresh, not past max hours, no RBAC issue')
        return sq_obj

    def _reask_do(self, sq_obj):
        def stats():
            value = [
                f'attempts #{attempts}/{max_attempts}',
                f'sleep={REASK_SLEEP}',
                f'orig_qid={orig_qid}',
                f'new_qid={new_qid}',
            ]
            return ', '.join(value)

        def pre():
            return f'{sq_info(sq_obj)} [REASK DO] '

        attempts = 0
        max_attempts = REASK_RETRIES
        orig_qid = get_qid(sq_obj=sq_obj)
        new_qid = orig_qid
        logger.info(f'{pre()}START: {stats()}')

        while True:
            time.sleep(REASK_SLEEP)
            orig_qid = get_qid(sq_obj=sq_obj)
            sq_obj = self._refetch_sq(sq_obj=sq_obj)
            sq_obj = self._wait_for_expiry(sq_obj=sq_obj)

            result_infos = self._get_result_info_sq(sq_id=sq_obj['id'])
            result_info = result_infos['result_infos'][0]
            new_qid = result_info['question_id']

            if new_qid != orig_qid:
                sq_obj['question'] = self._get_q(qid=new_qid)
                if self._rbac_gri_ok(qid=new_qid):
                    logger.info(f'{pre()}DONE issued new qid from SQ GRI and GRI RBAC OK: {stats()}')
                    return sq_obj

                logger.info(f'{pre()}ERROR issued new qid from SQ GRI and GRI RBAC FAIL: {stats()}')
                sq_obj = self._wait_for_expiry(sq_obj=sq_obj)
            else:
                logger.info(f'{pre()}no new qid from SQ GRI: {stats()}')

            time.sleep(5)
            sq_obj = self._refetch_sq(sq_obj=sq_obj)
            new_qid = get_qid(sq_obj=sq_obj)

            if new_qid != orig_qid:
                if self._rbac_gri_ok(qid=new_qid):
                    logger.info(f'{pre()}DONE issued new qid from SQ refetch and GRI RBAC OK: {stats()}')
                    return sq_obj

                logger.info(f'{pre()}ERROR issued new qid from SQ refetch and GRI RBAC FAIL: {stats()}')
                self._wait_for_expiry(sq_obj=sq_obj)

            if attempts >= max_attempts:
                raise RESTException(f'{pre()}ERROR wait for new qid retry limit hit: {stats()}')

            logger.info(f'{pre()}WAIT qid unchanged: {stats()}')
            attempts += 1

    def _wait_for_expiry(self, sq_obj):
        def stats():
            value = [
                f'qid change #{changes}/{max_changes}',
                f'sleep={sleep}',
                f'orig_qid={orig_qid}',
                f'new_qid={new_qid}',
            ]
            return ', '.join(value)

        def pre():
            return f'{sq_info(sq_obj)} [WAIT FOR EXPIRY] '

        guess = '(admin has SQ open for editing?)'
        changes = 0
        max_changes = 2
        sleep = 5
        orig_qid = get_qid(sq_obj=sq_obj)
        new_qid = orig_qid

        while not get_expiry(sq_obj=sq_obj)['is_expired']:
            logger.info(f'{pre()}not expired yet: {stats()}')
            sq_obj = self._refetch_sq(sq_obj=sq_obj)
            new_qid = get_qid(sq_obj=sq_obj)

            if orig_qid != new_qid:
                if changes >= max_changes:
                    raise RESTException(f'{pre()}QID changed to many times {guess}: {stats()}')

                logger.error(f'{pre()}WARNING qid changed {guess}: {stats()}')
                changes += 1
                orig_qid = new_qid

            time.sleep(sleep)

        logger.info(f'{pre()}expired: {stats()}')
        return sq_obj

    # pylint: disable=too-many-locals
    def _poll_answers(self, sq_obj):
        """Poll a question ID until question expiry or all answers in.

        Question expiry is normally 10 minutes after the question is asked.
        Expiry means that no more answers
        will come from endpoints, so what has been received so far is all there is.

        Data for a question is normally only available for 5 minutes after expiry,
        unless it's a question asked by a saved question.
        """

        def stats():
            value = [
                f'poll #{poll}',
                f'sleep={SLEEP_POLL_ANSWERS}',
                f'is_done={is_done}',
                f'answered_count={answered_count}',
                f'total_count={total_count}',
                f'minutes_spent_polling={minutes_spent_polling}',
            ]
            return ', '.join(value)

        def pre():
            return f'{sq_info(sq_obj)} [POLL_ANSWERS] '

        q_obj = sq_obj['question']
        start = tanium.tools.dt_now()
        poll = 1
        is_done = False
        minutes_spent_polling = 0
        answered_count = 0
        total_count = 0

        while not get_expiry(sq_obj=sq_obj)['is_expired']:
            result_infos = self._get_result_info_q(qid=q_obj['id'])
            result_info = result_infos['result_infos'][0]
            logger.info(f'{pre()}RESULT_INFO {kvdump(result_info)}')

            total_count = result_info['estimated_total']
            answered_count = result_info['mr_tested']
            # mr_tested:
            # The number of machines that evaluated the question filter and are within the
            # groups to which you have access. For example, if you get computer name from
            # Windows machines, mr_tested would be the number of machines in the groups
            # that you have access to and that evaluated if they were Windows machines
            # (the machines do not need to be Windows machines). When the value of
            # estimated_total matches mr_tested, the question results are ready to be retrieved.

            is_done = answered_count >= total_count
            minutes_spent_polling = tanium.tools.dt_calc_mins(value=start, reverse=False)

            if is_done:
                logger.info(f'{pre()}DONE answered_count >= total_count: {stats()}')
                return sq_obj

            logger.info(f'{pre()}WAIT answered_count not >= total_count: {stats()}')

            poll += 1
            time.sleep(SLEEP_POLL_ANSWERS)

        logger.info(f'{pre()}DONE is expired: {stats()}')
        return sq_obj

    def _get_answers(
        self, sq_obj, options=None, page_size=PAGE_SIZE, page_sleep=SLEEP_GET_ANSWERS,
    ):
        """Get results."""

        def stats():
            value = [
                f'page #{page}',
                f'fetched_cnt={fetched_cnt}',
                f'row_cnt_page={len(rows)}',
                f'row_cnt={row_cnt}',
                f'row_start={row_start}',
                f'minutes_taken={minutes_taken}',
                f'page_size={page_size}',
                f'page_sleep={page_sleep}',
            ]
            return ', '.join(value)

        def pre():
            return f'{sq_info(sq_obj)} [GET_ANSWERS] '

        q_obj = sq_obj['question']
        start = tanium.tools.dt_now()
        page = 1
        row_start = 0
        fetched_cnt = 0
        columns_map = {}
        cache_id = 0
        minutes_taken = None
        rows = []
        logger.info(f'{pre()}START')

        while fetched_cnt < MAX_DEVICES_COUNT:
            options = options or {}
            options['row_start'] = row_start
            options['row_count'] = page_size
            # row_start/row_count: select a subset of the result data.

            options['cache_expiration'] = CACHE_EXPIRATION
            # cache_expiration:
            # The number of seconds (600 max) the cache remains in memory on the server.
            # Each request renews the specified cache. Setting cache_expiration to 0 expires the cache.

            if cache_id:
                options['cache_id'] = cache_id

            result_datas = self._get_result_data_q(qid=q_obj['id'], options=options)
            result_data = result_datas['result_sets'][0]
            columns = result_data.pop('columns', [])
            rows = result_data.pop('rows', [])

            logger.debug(f'{pre()}RESULT_DATA {kvdump(result_data)}')

            row_cnt = result_data['row_count']
            cache_id = result_data['cache_id']
            # cache_id: Use cache_id in subsequent requests to use this cache for performance gains.

            fetched_cnt += len(rows)
            minutes_taken = tanium.tools.dt_now() - start
            got_all_answers = fetched_cnt >= row_cnt

            if not rows:
                logger.info(f'{pre()}DONE: no rows returned: {stats()}')
                break

            if not columns_map:
                columns_map = self._map_sensors_to_columns(src=pre(), columns=columns)

            for row in rows:
                yield self._get_row_map(src=pre(), row=row, columns_map=columns_map), q_obj

            if fetched_cnt >= row_cnt:
                logger.info(f'{pre()}DONE: fetched_cnt >= row_cnt: {stats()}')
                break

            logger.info(f'{pre()}WAIT: fetched_cnt not >= row_cnt: {stats()}')

            row_start += page_size
            page += 1
            time.sleep(page_sleep)

    @staticmethod
    def _get_row_map(row, columns_map, src=''):
        """Parse a row of values based on the sensors defined in columns_map."""
        row_map = {}
        pre = f'{src} row map: '
        if 'cid' in row and CID_SENSOR not in columns_map:
            # this is an odd thing. it probably is from force_computer_id_flag=1, but that seems to need to be
            # set at SQ/Q creation time via the API only (not the GUI!)
            row_map[CID_SENSOR] = {'value': row['cid'], 'type': 'String'}

        row_data = row['data']

        if 'Count' in columns_map:
            column_idx, column_info = list(columns_map['Count'].items())[0]
            row_column_values = row_data[column_idx][0]['text']
            if row_column_values not in ['1', 1]:
                logger.error(f'{pre}Count value of {row_column_values!r} is not 1, skipping!')
                return None

        for sensor_name, columns in columns_map.items():
            if sensor_name == 'Count':
                continue

            if sensor_name not in row_map:
                row_map[sensor_name] = {}

            first_column_idx, first_column_info = list(columns.items())[0]
            first_row_column_values = [x['text'] for x in row_data[first_column_idx]]

            if len(columns) == 1:
                # simple single column sensor
                column_name = first_column_info['name']
                column_type = first_column_info['type']
                row_map[column_name] = {
                    'type': column_type,
                    'value': first_row_column_values,
                }
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

    def _map_sensors_to_columns(self, columns, src=''):
        """Get a mapping of sensor names to their respective columns returned."""
        sensors_by_hash = {}
        sensors_to_columns = {}
        pre = f'{src}sensor to column map: '

        internal_cols = ['Count', 'Age']
        # Count is the number of identical results from endpoints for this row
        # Age is only present when most_recent_flag=1 and represents the age of the data in the row

        # More about Age, re: recent_results_buckets
        # A comma-separated list of integers. If empty or unspecified,
        # the default value is "600,3600,86400,604800". When the most_recent_flag field is set to 1,
        # results that are identical other than age are grouped into age range buckets.
        # By default, all ages less than 600 seconds are in the first ("current results") group.
        # The second group contains all ages less than 3600 seconds, but greater than or equal to 600.
        # The final group includes all ages greater than the last specified range.
        # You may include any number of buckets.

        # this may mean we get duplicate rows for the same CID from results when most_recent_flag=1
        # we need to see what this looks like in adapter code

        for column_idx, column in enumerate(columns):
            column_name = column['name']
            column_hash = column['hash']

            cdesc = [
                f'column #{column_idx}',
                f'name={column_name!r}',
                f'sensor hash={column_hash!r}',
            ]
            cdesc = ', '.join(cdesc)

            if column_name in internal_cols:
                sensors_to_columns[column_name] = {column_idx: {'name': column_name, 'type': 'int'}}
                continue

            if column['hash'] not in sensors_by_hash:
                try:
                    # Fetch the sensor object by the hash value for this column.
                    sensor = self._get_by_hash(objtype='sensors', value=column['hash'])
                    sensor_name = sensor['name']

                    # add it to sensor cache so other columns for this sensor don't
                    # have to refetch the object
                    sensors_by_hash[column_hash] = sensor

                    msg = f'{pre}Fetched uncached sensor {sensor_name!r} for: {cdesc}'
                    logger.debug(msg)
                except Exception:
                    # this shouldn't happen
                    msg = f'{pre}Failed to fetch sensor for: {cdesc}'
                    logger.exception(msg)
                    raise

                # get subcolumn name and value types defined for this sensor,
                # if any subcolumns defined
                # if subcolumns defined, its an object in axonius
                sensor['column_map'] = {x['name']: x['value_type'] for x in sensor.get('subcolumns', []) or []}

                # if no subcolumns defined in sensor, then the only column will be one
                # named after sensor name
                # with the value_type of the sensor itself
                if not sensor['column_map']:
                    sensor['column_map'] = {sensor_name: sensor['value_type']}
            else:
                # We've already fetched the sensor object by hash, get it from our cache
                sensor = sensors_by_hash[column_hash]
                sensor_name = sensor['name']
                logger.debug(f'{pre}Found cached sensor {sensor_name!r} for: {cdesc}')

            col_map = sensor['column_map']
            if column_name not in col_map:
                # this shouldn't happen
                msg = f'{pre}Failed to find column in subcolumns {col_map} for: {cdesc}'
                logger.error(msg)
                continue

            if sensor_name not in sensors_to_columns:
                sensors_to_columns[sensor_name] = {}

            sensors_to_columns[sensor_name][column_idx] = {
                'name': column_name,
                'type': sensor['column_map'][column_name],
            }

        return sensors_to_columns
