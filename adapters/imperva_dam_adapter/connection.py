import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class ImpervaDamConnection(RESTConnection):
    """ rest client for ImpervaDam adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='SecureSphere/api/v1/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._post('auth/session', do_basic_auth=True)
        self._get('conf/agents')

    def get_device_list(self):
        agents = self._get('conf/agents')['agents']
        for agent_raw in agents:
            agent_name = agent_raw.get('name')
            if not agent_name:
                continue
            try:
                agent_raw['open_ports'] = self._get(f'conf/agents/{agent_name}/dataInterfaces')['data-interfaces']
            except Exception:
                logger.exception(f'Problem with open_ports for agent_raw {agent_raw}')

            try:
                agent_raw['advanced_config'] = self._get(
                    f'conf/agents/{agent_name}/Settings/AdvancedConfiguration')['agent-config']
            except Exception:
                logger.exception(f'Problem with advanced_config for agent_raw {agent_raw}')

            try:
                agent_raw['general_details'] = self._get(f'conf/agents/{agent_name}/GeneralDetails')
            except Exception:
                logger.exception(f'Problem with general_details for agent_raw {agent_raw}')

            try:
                agent_raw['cpu_usage'] = self._get(f'conf/{agent_name}/Settings/CPUUsageRestraining')
            except Exception:
                logger.exception(f'Problem with cpu_usage for agent_raw {agent_raw}')

            try:
                agent_raw['discovery_settings'] = self._get(f'conf/agents/{agent_name}/Settings/DiscoverySettings')
            except Exception:
                logger.exception(f'Problem with DiscoverySettings for agent_raw {agent_raw}')

            try:
                agent_raw['agent_tags'] = self._get(f'conf/agents/{agent_name}/tags/')['tags']
            except Exception:
                logger.exception(f'Problem with agent_tags for agent_raw {agent_raw}')

            yield agent_raw
