import json

import pytest

import services.plugin_service as plugin_service
from services.simple_fixture import initialize_fixture


class GuiService(plugin_service.PluginService):
    def __init__(self, compose_file_path='../plugins/gui/docker-compose.yml',
                 config_file_path='../plugins/gui/src/plugin_config.ini',
                 container_name='gui'):
        super().__init__(compose_file_path, config_file_path, container_name)

    def get_devices(self, *kargs, **kwargs):
        return self.get('devices', *kargs, **kwargs)

    def get_device_by_id(self, id, *kargs, **kwargs):
        return self.get('devices/{0}'.format(id), *kargs, **kwargs)

    def get_all_tags(self, *kargs, **kwargs):
        return self.get('tags', *kargs, **kwargs)

    def remove_tags_from_device(self, id, tag_list, *kargs, **kwargs):
        return self.delete('devices/{0}/tags'.format(id), data=json.dumps(tag_list), *kargs, **kwargs)

    def add_tags_to_device(self, id, tag_list, *kargs, **kwargs):
        return self.post('devices/{0}'.format(id), data=json.dumps(tag_list), *kargs, **kwargs)

    def get_queries(self):
        self.get('trigger_watches', api_key=self.api_key)


@pytest.fixture(scope="module")
def gui_fixture(request):
    service = GuiService()
    initialize_fixture(request, service)
    return service
