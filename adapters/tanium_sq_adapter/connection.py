import time
from datetime import timedelta

import logging

from axonius.clients.rest.connection import RESTException
from axonius.clients import tanium
from tanium_sq_adapter.consts import (
    PAGE_SIZE,
    MAX_DEVICES_COUNT,
    SLEEP_REASK,
    SLEEP_GET_ANSWERS,
    SLEEP_POLL_ANSWERS,
    REQUIRED_SENSORS,
    RETRIES_REASK,
    CACHE_EXPIRATION,
    HEADERS,
)

logger = logging.getLogger(f'axonius.{__name__}')


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
    def get_device_list(self, client_name, client_config):
        server_version = self._get_version()
        workbenches = self._get_workbenches_meta()

        metadata = {
            'server_name': client_config['domain'],
            'client_name': client_name,
            'server_version': server_version,
            'workbenches': workbenches,
        }

        sqargs = {
            'refresh': client_config.get('sq_refresh', False),
            'max_hours': client_config.get('sq_max_hours', 24),
            'no_results_wait': client_config.get('no_results_wait', True),
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

    def _get_sq_results(self, name, no_results_wait=True, refresh=False, max_hours=0):
        """Get the results from a saved question.

        Args:
            name: Name of the saved question to get results for.
            sleep_poll: Sleep for polling loop for _poll_answers.
            sleep_get_result: Sleep for polling for _get_answers.
            refresh: Re-ask the question for the SQ no matter what.
            max_hours: Re-ask the question for the SQ if last asked question is more
                       than this many hours ago.
        """
        pre = 'Saved Question Get Results: '
        # get the SQ object as dict
        saved_question = self._get_sq(name=name)

        sq_name = saved_question['name']

        if saved_question.get('question'):
            # SQ was asked before
            question = saved_question['question']
            question_id = question['id']
            query = question['query_text']
            expire_dt = tanium.tools.parse_dt(value=question['expiration'], src=question)
            is_expired = tanium.tools.dt_is_past(value=expire_dt, src=question)
            never_asked = False
            do_refresh = False
            is_past_max_hours = False

            if max_hours:
                # see if question for SQ expiry date is more than max_hours ago
                is_past_max_hours = (tanium.tools.dt_now() - timedelta(hours=max_hours)) >= expire_dt

            if is_expired and (refresh or is_past_max_hours):
                do_refresh = True
        else:
            # SQ has never been asked
            question = None
            question_id = None
            query = None
            expire_dt = None
            is_expired = True
            never_asked = True
            do_refresh = True
            is_past_max_hours = True

        mins_left = tanium.tools.dt_calc_mins(value=expire_dt, reverse=True)
        stats = [
            f'{pre}name={name!r}',
            f'expire time={expire_dt}, in {mins_left} mins, is expired={is_expired}',
            f'expire time is past max hours {max_hours}={is_past_max_hours}',
            f'will be re-asked={do_refresh}, was never asked={never_asked}, always re-ask={refresh}',
            f'will wait for no results answers to go away={no_results_wait}',
            f'question ID {question_id} with query={query!r}, ',
        ]
        stats = '\n  '.join(stats)
        logger.info(stats)

        if do_refresh:
            # issue a new question for SQ
            saved_question = self._reask(saved_question=saved_question)
            question = saved_question['question']

        # wait till either all answers are in for question for SQ
        # or expiry of question for SQ has hit (10 minutes after it was asked)
        self._poll_answers(question_id=question['id'], no_results_wait=no_results_wait)

        yield from self._get_answers(question=question)

    def _poll_answers(self, question_id, no_results_wait=True):
        """Poll a question ID until question expiry or all answers in.

        Question expiry is normally 10 minutes after the question is asked. Expiry means that no more answers
        will come from endpoints, so what has been received so far is all there is.

        Data for a question is normally only available for 5 minutes after expiry,
        unless it's a question asked by a saved question.
        """
        pre = 'Saved Question Poll Answers: '
        start = tanium.tools.dt_now()

        poll_count = 1

        while True:
            question = self._get_by_id(objtype='questions', value=question_id)

            query = question['query_text']
            expire_dt = tanium.tools.parse_dt(value=question['expiration'], src=question)
            is_expired = tanium.tools.dt_is_past(value=expire_dt, src=question)
            poll_info = [
                f'poll #{poll_count} for answers for id={question_id}',
                f'expired={is_expired}',
                f'no results wait={no_results_wait}',
            ]
            poll_info = ', '.join(poll_info)
            try:
                datas = self._tanium_get(endpoint=f'result_info/question/{question_id}')
            except Exception:
                # added due to RBAC failure to fetch result info for a question
                # unsure why this happens, but it seems like a bug in tanium
                # since a limited permissions user can ask this question fine in the console
                logger.exception(f'{pre}ERROR {poll_info}')
                if is_expired:
                    logger.info(f'{pre}DONE is expired {poll_info}')
                    break
                poll_count += 1
                time.sleep(SLEEP_POLL_ANSWERS)
                continue
            try:
                data = datas['result_infos'][0]
                total = data['estimated_total']
                passed = data['mr_passed']
                no_results_cnt = data['no_results_count']
                answers_are_in = passed >= total

                mins_wait = tanium.tools.dt_calc_mins(value=start, reverse=False)
                mins_left = tanium.tools.dt_calc_mins(value=expire_dt, reverse=True)

                stats = [
                    f'{poll_info} answers in: {passed}/{total} ({no_results_cnt} with no results)',
                    f'expires in: {mins_left}m been waiting for: {mins_wait}m',
                ]
                stats = ', '.join(stats)

                if is_expired:
                    logger.info(f'{pre}DONE is expired for {stats}')
                    break

                if answers_are_in:
                    if no_results_cnt:
                        if no_results_wait:
                            logger.debug(f'{pre}WAIT all answers in, but some have no results for {stats}')
                        else:
                            logger.debug(f'{pre}DONE all answers in, but some have no results for {stats}')
                            break
                    else:
                        logger.info(f'{pre}DONE all answers are in for {stats}')
                        break
                else:
                    logger.debug(f'{pre}WAIT for more answers for {stats}')

                poll_count += 1
                time.sleep(SLEEP_POLL_ANSWERS)
            except Exception:
                logger.exception(f'{pre}ERROR during fetch result_info')
                break

    def _reask(self, saved_question):
        pre = 'Saved Question Re-Ask: '
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
            stats = [
                f'saved question name: {sq_name!r}, try #{tries} out of {RETRIES_REASK}',
                f'question old_id: {old_id!r}, new_id: {new_id!r}, asked before: {asked_before}',
            ]
            stats = ', '.join(stats)

            if tries > RETRIES_REASK:
                msg = f'{pre}ERROR retry limit hit while waiting for new question for {stats}'
                logger.info(msg)
                raise RESTException(msg)

            if new_id and (not asked_before or (asked_before and (new_id != old_id))):
                logger.info(f'{pre}DONE issued new question for {stats}')
                break

            logger.info(f'{pre}WAIT checking for new question for {stats}')

            u_saved_question = self._get_by_id(objtype='saved_questions', value=saved_question['id'])
            new_id = u_saved_question.get('question', {}).get('id')
            tries += 1
            time.sleep(SLEEP_REASK)

        return u_saved_question

    def _get_answers(self, question, options=None):
        """Get results."""
        pre = 'Saved Question Get Answers: '
        start = tanium.tools.dt_now()

        page = 1
        row_start = 0
        fetched = 0
        columns_map = {}
        cache_id = 0

        logger.info(f'{pre}started fetch for id={question["id"]}')

        while fetched < MAX_DEVICES_COUNT:
            options = options or {}
            options['row_start'] = row_start
            options['row_count'] = PAGE_SIZE
            options['cache_expiration'] = CACHE_EXPIRATION

            if cache_id:
                options['cache_id'] = cache_id

            datas = self._tanium_get(endpoint=f'result_data/question/{question["id"]}', options=options)
            data = datas['result_sets'][0]
            columns = data.pop('columns')
            rows = data.pop('rows')

            cache_id = data['cache_id']
            total = data['estimated_total']
            fetched += len(rows)
            time_taken = tanium.tools.dt_now() - start

            stats = f'page={page}, fetched=[{fetched}/{total}], time_taken={time_taken}'

            if not rows:
                logger.info(f'{pre}DONE no rows returned for {stats}')
                break

            logger.debug(f'{pre}WAIT rows returned for {stats}')

            if not columns_map:
                columns_map = self._map_sensors_to_columns(columns=columns)

            for row in rows:
                yield self._get_row_map(row=row, columns_map=columns_map), question

            if fetched >= total:
                logger.info(f'{pre}DONE hit rows total for {stats}')
                break

            row_start += PAGE_SIZE
            page += 1
            time.sleep(SLEEP_GET_ANSWERS)

    @staticmethod
    def _get_row_map(row, columns_map):
        """Parse a row of values based on the sensors defined in columns_map."""
        pre = 'Saved Question Row Map: '
        row_map = {}

        if 'cid' in row and 'Computer ID' not in columns_map:
            # this is an odd thing. I've seen cid returned, i've seen it not... shrug
            row_map['Computer ID'] = {'value': row['cid'], 'type': 'String'}

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
        pre = 'Saved Question Column Map: '
        sensors_by_hash = {}
        sensors_to_columns = {}

        for column_idx, column in enumerate(columns):
            column_name = column['name']
            column_hash = column['hash']

            column_desc = f'column #{column_idx}, name={column_name!r}, sensor hash={column_hash!r}'

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

                    msg = f'{pre}Fetched uncached sensor {sensor_name!r} for: {column_desc}'
                    logger.debug(msg)
                except Exception:
                    # this shouldn't happen
                    msg = f'{pre}Failed to fetch sensor for: {column_desc}'
                    logger.exception(msg)
                    raise

                # get subcolumn name and value types defined for this sensor, if any subcolumns defined
                # if subcolumns defined, its an object in axonius
                sensor['column_map'] = {x['name']: x['value_type'] for x in sensor.get('subcolumns', []) or []}

                # if no subcolumns defined in sensor, then the only column will be one named after sensor name
                # with the value_type of the sensor itself
                if not sensor['column_map']:
                    sensor['column_map'] = {sensor_name: sensor['value_type']}
            else:
                # We've already fetched the sensor object by hash, get it from our cache
                sensor = sensors_by_hash[column_hash]
                sensor_name = sensor['name']
                logger.debug(f'{pre}Found cached sensor {sensor_name!r} for: {column_desc}')

            if column_name not in sensor['column_map']:
                # this shouldn't happen
                logger.error(f'{pre}Failed to find column in subcolumns {sensor["column_map"]} for: {column_desc}')
                continue

            if sensor_name not in sensors_to_columns:
                sensors_to_columns[sensor_name] = {}

            sensors_to_columns[sensor_name][column_idx] = {
                'name': column_name,
                'type': sensor['column_map'][column_name],
            }

        return sensors_to_columns
