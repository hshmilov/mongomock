from threading import Thread

from axonius.adapter_base import AdapterBase
from axonius.device import Device
from axonius.utils.files import get_local_config_file
from qcore_adapter.protocol.consts import PUMP_SERIAL
from qcore_adapter.qcore_mongo import QcoreMongo
from qcore_adapter.server.mediator_server import run_mediator_server


class QcoreAdapter(AdapterBase):
    class MyDevice(Device):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

        # adding client is not relevant here...
        self._add_client({'mediator': '1'})
        self.thread = Thread(target=run_mediator_server)
        self.thread.start()

    def _connect_client(self, client_config):
        return {'mediator': '1'}

    def populate_nic(self, device, pump_document):
        try:
            mac = pump_document['clinical_status']['Connectivity']['mac']
            ip = pump_document['clinical_status']['Connectivity']['ip_address']
            device.add_nic(mac=mac, ips=[ip], logger=self.logger)
        except:
            self.logger(f"failed to populate nic info")

    def _query_devices_by_client(self, client_name, client_data):
        qcore_mongo = QcoreMongo()
        return list(qcore_mongo.all_pumps)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "mediator",
                    "title": "Qcore mediator",
                    "type": "string"
                }
            ],
            "required": [
                "mediator"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for pump_document in devices_raw_data:
            device = self._new_device()
            device.id = pump_document[PUMP_SERIAL]
            self.populate_nic(device, pump_document)
            device.set_raw(pump_document)
            yield device

    def _get_client_id(self, client_config):
        return client_config['mediator']
