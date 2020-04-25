import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HpNnmiXmlService(AdapterService):
    def __init__(self):
        super().__init__('hp-nnmi-xml')


@pytest.fixture(scope='module', autouse=True)
def hp_nnmi_xml_fixture(request):
    service = HpNnmiXmlService()
    initialize_fixture(request, service)
    return service
