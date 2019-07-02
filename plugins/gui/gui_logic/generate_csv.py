from datetime import datetime

from flask import Response

from axonius.entities import EntityType
from axonius.plugin_base import PluginBase
from axonius.consts.plugin_consts import HEAVY_LIFTING_PLUGIN_NAME

CHUNK_SIZE = 1024


def get_csv_from_heavy_lifting_plugin(mongo_filter, mongo_sort, mongo_projection, history: datetime,
                                      entity_type: EntityType, default_sort: bool) -> Response:
    """
    Queries the heavy lifting plugin and asks it to process the csv request.
    All the params are documented in the respected decorators in gui/service.py
    """
    timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')
    headers = {
        'Content-Disposition': f'attachment; filename=axonius-data_{timestamp}.csv',
        'Content-Type': 'text/csv'
    }
    res = _get_csv_from_heavy_lifting(default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort)

    def generate():
        for chunk in res.iter_content(CHUNK_SIZE):
            yield chunk

    return Response(generate(), headers=headers)


def get_csv_file_from_heavy_lifting_plugin(output_path, query_name, mongo_filter, mongo_sort,
                                           mongo_projection, history: datetime,
                                           entity_type: EntityType, default_sort: bool) -> str:
    """
    Queries the heavy lifting plugin and asks it to process the csv request.
    All the params are documented in the respected decorators in gui/service.py

    :return: the generated csv file of the saved query.
    """
    timestamp = datetime.now().strftime('%m-%d-%Y-%H:%M:%S')
    res = _get_csv_from_heavy_lifting(default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort)

    temp_csv_filename = f'{output_path}{query_name[0:100]}_{timestamp}.csv'
    with open(temp_csv_filename, 'wb') as file:
        for chunk in res.iter_content(CHUNK_SIZE):
            file.write(chunk)
    return temp_csv_filename


def _get_csv_from_heavy_lifting(default_sort, entity_type, history, mongo_filter, mongo_projection, mongo_sort):
    return PluginBase.Instance.request_remote_plugin('generate_csv', HEAVY_LIFTING_PLUGIN_NAME,
                                                     'post',
                                                     json={
                                                         'mongo_filter': mongo_filter,
                                                         'mongo_sort': mongo_sort,
                                                         'mongo_projection': mongo_projection,
                                                         'entity_type': entity_type.value,
                                                         'default_sort': default_sort,
                                                         'history': history
                                                     }, stream=True)
