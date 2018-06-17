import pytest

from services.axonius_service import get_service
from services.plugin_service import AdapterService
from services.ports import DOCKER_PORTS
from services.simple_fixture import initialize_fixture


class QcoreService(AdapterService):
    def __init__(self):
        super().__init__('qcore')

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)

        axonius_service = get_service()

        axonius_service.set_system_settings({
            "refreshRate": 1,
            "singleAdapter": True,
            "multiLine": True
        })

        axonius_service.set_research_rate(0.0001)

        infusion_fields = [
            "adapters_data.qcore_adapter.pump_serial",
            "adapters_data.qcore_adapter.inf_time_remaining",
            "adapters_data.qcore_adapter.inf_volume_remaining",
            "adapters_data.qcore_adapter.inf_volume_infused",
            "adapters_data.qcore_adapter.inf_line_id",
            "adapters_data.qcore_adapter.inf_is_bolus",
            "adapters_data.qcore_adapter.inf_bolus_data",
            "adapters_data.qcore_adapter.inf_medication",
            "adapters_data.qcore_adapter.inf_cca",
            "adapters_data.qcore_adapter.inf_delivery_rate",
            "adapters_data.qcore_adapter.inf_infusion_event",
            "adapters_data.qcore_adapter.inf_dose_rate",
            "adapters_data.qcore_adapter.inf_dose_rate_units",
            "adapters_data.qcore_adapter.inf_status",
            "adapters_data.qcore_adapter.inf_total_bag_volume_delivered",
            "adapters_data.qcore_adapter.gen_device_context_type"
        ]
        axonius_service.add_view({
            "name": "Infusion",
            "view": {
                "page": 0,
                "pageSize": 20,
                "fields": infusion_fields,
                "coloumnSizes": [],
                "query": {
                    "filter": "adapters_data.qcore_adapter.inf_status == size(1) or adapters_data.qcore_adapter.inf_status == size(2)",
                },
                "sort": {
                    "field": "adapters_data.qcore_adapter.pump_serial",
                    "desc": True
                }
            },
            "query_type": "saved"
        })

        technician_fields = [
            "specific_data.data.network_interfaces.ips",
            "adapters_data.qcore_adapter.pump_serial",
            "adapters_data.qcore_adapter.connection_status",
            "adapters_data.qcore_adapter.pump_name",
            "adapters_data.qcore_adapter.sw_version",
            "adapters_data.qcore_adapter.dl_version",
            "adapters_data.qcore_adapter.location",
            "adapters_data.qcore_adapter.disconnects"
        ]
        axonius_service.add_view({
            "name": "Technician",
            "view": {
                "page": 0,
                "pageSize": 20,
                "fields": technician_fields,
                "coloumnSizes": [],
                "query": {
                    "filter": ""
                },
                "sort": {
                    "field": "",
                    "desc": True
                }
            },
            "query_type": "saved"
        })

        axonius_service.add_view({
            "name": "offline during infusion",
            "view": {
                "page": 0,
                "pageSize": 20,
                "fields": infusion_fields,
                "coloumnSizes": [],
                "query": {
                    "filter": "adapters_data.qcore_adapter.connection_status == \"offline\" and adapters_data.qcore_adapter.gen_device_context_type == \"Infusing\""
                },
                "sort": {
                    "field": "",
                    "desc": True
                }
            },
            "query_type": "saved"
        })

        axonius_service.add_view({
            "name": "Saphire 14.5",
            "view": {
                "page": 0,
                "pageSize": 20,
                "fields": technician_fields,
                "coloumnSizes": [],
                "query": {
                    "filter": "adapters_data.qcore_adapter.sw_version == regex(\"14.5\", \"i\")"
                },
                "sort": {
                    "field": "",
                    "desc": True
                }
            },
            "query_type": "saved"
        })

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS[self.container_name], 443),
                (DOCKER_PORTS['qcore-mediator'], DOCKER_PORTS['qcore-mediator'])]


@pytest.fixture(scope="module", autouse=True)
def qcore_fixture(request):
    service = QcoreService()
    initialize_fixture(request, service)
    return service
