import logging

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class TripWireEnterpriseConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         url_base_prefix='api/v1',
                         headers={'Content-Type': 'application/json-rpc', 'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        self._get('operations/operations', do_basic_auth=True)

    def get_device_list(self):
        operations = self._get('operations/operations', do_basic_auth=True)
        for operation in operations:
            try:
                source_id = operation.get('sourceId')
                external_id = operation.get('externalId')
                if not source_id or not external_id:
                    logging.warning(f'Bad operation with bad IDs {operation}')
                    continue
                asset_per_operation = self._get(f'operations/{source_id}/{external_id}/assets',
                                                do_basic_auth=True)
                for asset in asset_per_operation:
                    asset['operation'] = operation
                    yield asset
            except Exception:
                logger.exception(f'Problemg getting operation {operation}')
