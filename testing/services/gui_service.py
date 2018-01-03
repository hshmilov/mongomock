import json

import pytest

from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture


class GuiService(PluginService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../plugins/gui', **kwargs)

    def get_devices(self, *vargs, **kwargs):
        return self.get('devices', *vargs, **kwargs)

    def get_device_by_id(self, id, *vargs, **kwargs):
        return self.get('devices/{0}'.format(id), *vargs, **kwargs)

    def get_all_tags(self, *vargs, **kwargs):
        return self.get('tags', *vargs, **kwargs)

    def remove_tags_from_device(self, id, tag_list, *vargs, **kwargs):
        return self.delete('devices/{0}/tags'.format(id), data=json.dumps(tag_list), *vargs, **kwargs)

    def add_tags_to_device(self, id, tag_list, *vargs, **kwargs):
        return self.post('devices/{0}'.format(id), data=json.dumps(tag_list), *vargs, **kwargs)

    def get_queries(self):
        self.get('trigger_watches', api_key=self.api_key)


@pytest.fixture(scope="module")
def gui_fixture(request):
    service = GuiService()
    initialize_fixture(request, service)
    return service
