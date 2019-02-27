import logging

from axonius.devices.device_adapter import AdapterProperty
from axonius.plugin_base import PluginBase
from axonius.utils.revving_cache import rev_cached

logger = logging.getLogger(f'axonius.{__name__}')


@rev_cached(ttl=120)
def get_dashboard_coverage():
    """
    Measures the coverage portion, according to sets of properties that devices' adapters may have.
    Portion is calculated out of total devices amount.
    Currently returns coverage for devices composed of adapters that are:
    - Managed ('Manager' or 'Agent')
    - Endpoint Protected
    - Vulnerability Assessed

    :return:
    """
    logger.info('Getting dashboard coverage')
    devices_total = PluginBase.Instance.devices_db.count_documents({
        'adapters': {
            '$elemMatch': {
                'pending_delete': {
                    '$ne': True
                }
            }
        }
    })
    if not devices_total:
        return []

    coverage_list = [
        {'name': 'managed_coverage', 'title': 'Managed Device',
         'properties': [AdapterProperty.Manager.name, AdapterProperty.Agent.name],
         'description': 'Deploy appropriate agents on unmanaged devices, and add them to Active Directory.'},
        {'name': 'endpoint_coverage', 'title': 'Endpoint Protection',
         'properties': [AdapterProperty.Endpoint_Protection_Platform.name],
         'description': 'Add an endpoint protection solution to uncovered devices.'},
        {'name': 'vulnerability_coverage', 'title': 'VA Scanner',
         'properties': [AdapterProperty.Vulnerability_Assessment.name],
         'description': 'Add uncovered devices to the next scheduled vulnerability assessment scan.'}
    ]
    for item in coverage_list:
        devices_property = PluginBase.Instance.devices_db.count_documents({
            'adapters.data.adapter_properties':
                {'$in': item['properties']}
        })
        item['portion'] = devices_property / devices_total

    return coverage_list
