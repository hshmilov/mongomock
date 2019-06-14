import logging

from flask import Response, jsonify

from axonius.entities import EntityType
from axonius.utils import gui_helpers
from axonius.consts.plugin_consts import HEAVY_LIFTING_PLUGIN_NAME
from axonius.plugin_base import PluginBase, add_rule
from axonius.utils.files import get_local_config_file

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=R0201
class HeavyLiftingService(PluginBase):
    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         requested_unique_plugin_name=HEAVY_LIFTING_PLUGIN_NAME,
                         *args, **kwargs)

    @add_rule('generate_csv', methods=['POST'])
    def generate_csv(self):
        kwargs = dict(self.get_request_data_as_object())
        kwargs['entity_type'] = EntityType(kwargs['entity_type'])

        res_iterator = gui_helpers.get_csv_iterable(**kwargs)
        return Response(res_iterator)

    @add_rule('tag_entities', methods=['POST'])
    def tag_entities(self):
        kwargs = dict(self.get_request_data_as_object())
        kwargs['entity'] = EntityType(kwargs['entity'])
        result = self.add_many_labels_to_entity(**kwargs)
        if kwargs.get('with_results'):
            return jsonify(result)
        return ''
