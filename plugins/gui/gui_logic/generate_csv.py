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
    res = PluginBase.Instance.request_remote_plugin('generate_csv', HEAVY_LIFTING_PLUGIN_NAME,
                                                    'post', json={
                                                        'mongo_filter': mongo_filter,
                                                        'mongo_sort': mongo_sort,
                                                        'mongo_projection': mongo_projection,
                                                        'entity_type': entity_type.value,
                                                        'default_sort': default_sort,
                                                        'history': history
                                                    }, stream=True)

    def generate():
        for chunk in res.iter_content(CHUNK_SIZE):
            yield chunk

    return Response(generate(), headers=headers)
