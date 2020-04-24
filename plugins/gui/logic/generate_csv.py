import codecs
import io
import logging
from datetime import datetime

import requests
from flask import Response

from axonius.entities import EntityType
from axonius.plugin_base import PluginBase, return_error
from axonius.consts.gui_consts import FILE_NAME_TIMESTAMP_FORMAT
from axonius.consts.plugin_consts import HEAVY_LIFTING_PLUGIN_NAME

CHUNK_SIZE = 1024
GENERATE_CSV_TIMEOUT = 60 * 5

logger = logging.getLogger(f'axonius.{__name__}')


def get_csv_from_heavy_lifting_plugin(mongo_filter, mongo_sort, mongo_projection, history: datetime,
                                      entity_type: EntityType, default_sort: bool,
                                      field_filters: dict = None, cell_joiner=None) -> Response:
    """
    Queries the heavy lifting plugin and asks it to process the csv request.
    All the params are documented in the respected decorators in gui/service.py
    """
    timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
    headers = {
        'Content-Disposition': f'attachment; filename=axonius-data_{timestamp}.csv',
        'Content-Type': 'text/csv'
    }
    res = _get_csv_from_heavy_lifting(
        default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort,
        field_filters, cell_joiner=cell_joiner)

    is_valid, response = validate_response(res)
    if not is_valid:
        return response

    def generate():
        # https://stackoverflow.com/questions/42715966/preserve-utf-8-bom-in-browser-downloads
        # Quote:
        # > I found a workaround by prepending two BOMs to the content,
        # > so there will be a BOM remaining after the first BOM gets removed by the browser.
        yield codecs.BOM_UTF8
        for chunk in res.iter_content(CHUNK_SIZE):
            yield chunk

    return Response(generate(), headers=headers)


def get_csv_file_from_heavy_lifting_plugin(query_name, mongo_filter, mongo_sort,
                                           mongo_projection, history: datetime, entity_type: EntityType,
                                           default_sort: bool, field_filters: dict = None,
                                           cell_joiner=None) -> object:
    """
    Queries the heavy lifting plugin and asks it to process the csv request.
    All the params are documented in the respected decorators in gui/service.py

    :return: the generated csv file of the saved query.
    """
    res = _get_csv_from_heavy_lifting(
        default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort, field_filters, cell_joiner)

    is_valid, response = validate_response(res)
    if not is_valid:
        return response

    csv_stream = io.StringIO()
    for chunk in res.iter_content(CHUNK_SIZE):
        csv_stream.write(chunk.decode('utf-8'))
    timestamp = datetime.now().strftime(FILE_NAME_TIMESTAMP_FORMAT)
    return {'name': f'{query_name[0:100]}_{timestamp}.csv', 'stream': csv_stream}


def _get_csv_from_heavy_lifting(default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort,
                                field_filters: dict = None, cell_joiner=None):
    try:
        return PluginBase.Instance.request_remote_plugin('generate_csv', HEAVY_LIFTING_PLUGIN_NAME,
                                                         'post',
                                                         json={
                                                             'mongo_filter': mongo_filter,
                                                             'mongo_sort': mongo_sort,
                                                             'mongo_projection': mongo_projection,
                                                             'entity_type': entity_type.value,
                                                             'default_sort': default_sort,
                                                             'cell_joiner': cell_joiner,
                                                             'history': history,
                                                             'field_filters': field_filters
                                                         }, stream=True, timeout=GENERATE_CSV_TIMEOUT)
    except requests.Timeout:
        return return_error('Connection timeout on request to heavy-lifting (for generating csv)')
    except requests.ConnectionError:
        return return_error('Connection error on request to heavy-lifting (for generating csv)')


def validate_response(res):
    """
    Make sure the response value is positive.
    :param res: response value, either  Response or return_error
    :return: bool (positive or negative response), object (return value)
    """
    if isinstance(res, requests.Response):
        if res.status_code != 200:
            logger.error(f'Error while generating csv file. Status code: {res.status_code}: {res.text}')
            return False, res
    else:
        logger.error(f'Error while generating csv file: {res}')
        return False, return_error('Error while generating csv file')
    return True, res
