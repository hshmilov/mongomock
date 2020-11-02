import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from g_naapi_adapter.structures import GNAApiDeviceType

logger = logging.getLogger(f'axonius.{__name__}')
ENTITIES_PER_PAGE = 100


class GNaapiConnection(RESTConnection):
    """ rest client for GNaapi adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')

        self._permanent_headers['x-api-key'] = self._apikey

        try:
            for _ in self.get_device_list(only_devices=True):
                break
        except Exception:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials')

    def naapi_get(self, endpoint, size=ENTITIES_PER_PAGE, search_after=None):
        url_params = {'size': size}
        if search_after:
            url_params['search_after'] = search_after

        return self._get(
            endpoint,
            url_params=url_params
        )

    def _paginated_device_get(self, endpoint: str):
        try:
            result = self.naapi_get(endpoint)
            hits = result.get('hits')
            if not isinstance(hits, dict) or not hits:
                raise ValueError(f'Invalid hits: {hits}')

            total = hits.get('total')
            logger.info(f'Endpoint "{endpoint}": total of {str(total)} entities')
            items = hits.get('hits') or []
            logger.debug(f'Endpoint "{endpoint}": Yielding {len(items)} items')
            for item in items:
                if item.get('_source'):
                    yield item.get('_source')

            while items:
                last_id = items[-1]['_id']
                result = self.naapi_get(endpoint, search_after=last_id)
                items = (result.get('hits') or {}).get('hits') or []
                logger.debug(f'Endpoint "{endpoint}": Yielding {len(items)} items')
                for item in items:
                    if item.get('_source'):
                        yield item.get('_source')
        except Exception:
            logger.exception(f'Invalid request made while paginating devices')
            raise

    # pylint: disable=too-many-branches, arguments-differ
    def get_device_list(self, only_devices=False):
        did_pull_one = False
        last_exc = None
        try:
            nic_id_to_nic_info = {}
            if not only_devices:
                logger.info(f'Pulling microsoft/network/networkinterfaces')
                try:
                    for nic in self._paginated_device_get('microsoft/network/networkinterfaces'):
                        if 'ResourceId' in nic and 'properties' in nic:
                            nic_id_to_nic_info[nic['ResourceId']] = nic['properties']
                except Exception:
                    logger.exception(f'Problem pulling microsoft/network/networkinterfaces, continuing')

            logger.info(f'Pulling microsoft/compute/virtualmachines')
            for device in self._paginated_device_get('microsoft/compute/virtualmachines'):
                did_pull_one = True
                network_interfaces_data = []
                device_properties = (device.get('properties') or {})
                for nic in (device_properties.get('networkProfile') or {}).get('networkInterfaces') or []:
                    nic_id = nic.get('id')
                    if nic_id and isinstance(nic_id, str) and nic_id in nic_id_to_nic_info:
                        network_interfaces_data.append(nic_id_to_nic_info[nic_id])

                if network_interfaces_data:
                    device['axonius_extended'] = {
                        'microsoft/network/networkinterfaces': network_interfaces_data
                    }
                yield device, GNAApiDeviceType.AzureCompute
        except RESTException as err:
            last_exc = err
            logger.exception(str(err))

        try:
            logger.info(f'Pulling geix/compute/server')
            for device in self._paginated_device_get('geix/compute/server'):
                did_pull_one = True
                yield device, GNAApiDeviceType.GEIXCompute
        except RESTException as err:
            last_exc = err
            logger.exception(str(err))

        try:
            logger.info(f'Pulling aws/ec2/instance')
            for device in self._paginated_device_get('aws/ec2/instance'):
                did_pull_one = True
                yield device, GNAApiDeviceType.AWSEC2
        except RESTException as err:
            last_exc = err
            logger.exception(str(err))

        if not did_pull_one:
            if last_exc:
                raise last_exc
            raise ValueError(f'Could not get devices - Please check credentials')

    @staticmethod
    def _paginated_user_get():
        yield from []

    def get_user_list(self):
        try:
            yield from self._paginated_user_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
