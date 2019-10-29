import codecs
import io
from datetime import datetime

from flask import Response

from axonius.entities import EntityType
from axonius.plugin_base import PluginBase
from axonius.consts.plugin_consts import HEAVY_LIFTING_PLUGIN_NAME

CHUNK_SIZE = 1024


def get_csv_from_heavy_lifting_plugin(mongo_filter, mongo_sort, mongo_projection, history: datetime,
                                      entity_type: EntityType, default_sort: bool,
                                      field_filters: dict = None) -> Response:
    """
    Queries the heavy lifting plugin and asks it to process the csv request.
    All the params are documented in the respected decorators in gui/service.py
    """
    timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
    headers = {
        'Content-Disposition': f'attachment; filename=axonius-data_{timestamp}.csv',
        'Content-Type': 'text/csv'
    }
    res = _get_csv_from_heavy_lifting(
        default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort, field_filters)

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
                                           default_sort: bool, field_filters: dict = None) -> object:
    """
    Queries the heavy lifting plugin and asks it to process the csv request.
    All the params are documented in the respected decorators in gui/service.py

    :return: the generated csv file of the saved query.
    """
    timestamp = datetime.now().strftime('%m-%d-%Y-%H:%M:%S')
    res = _get_csv_from_heavy_lifting(
        default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort, field_filters)

    temp_csv_filename = f'{query_name[0:100]}_{timestamp}.csv'
    csv_stream = io.StringIO()
    for chunk in res.iter_content(CHUNK_SIZE):
        csv_stream.write(chunk.decode('utf-8'))
    return {'name': temp_csv_filename, 'stream': csv_stream}


def _get_csv_from_heavy_lifting(default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort,
                                field_filters: dict = None):
    return PluginBase.Instance.request_remote_plugin('generate_csv', HEAVY_LIFTING_PLUGIN_NAME,
                                                     'post',
                                                     json={
                                                         'mongo_filter': mongo_filter,
                                                         'mongo_sort': mongo_sort,
                                                         'mongo_projection': mongo_projection,
                                                         'entity_type': entity_type.value,
                                                         'default_sort': default_sort,
                                                         'history': history,
                                                         'field_filters': field_filters
                                                     }, stream=True)
