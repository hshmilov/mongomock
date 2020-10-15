import sys

from scripts.instances.network_utils import get_docker_bridge_default_gateway
from services.weave_service import WeaveService, is_weave_up


class SystemService(WeaveService):
    """
    System services should be reachable from weave and docker networks.
    """

    def is_up(self, *args, **kwargs):
        pass

    def start(self,
              mode='',
              allow_restart=False,
              rebuild=False,
              hard=False,
              show_print=True,
              expose_port=False,
              extra_flags=None,
              docker_internal_env_vars=None,
              run_env=None):
        extra_flags = extra_flags or []
        if is_weave_up():
            # Docker will first try to resolve with the internal docker dns resolver,
            # and then use weave dns as a fallback
            dns_server_ip = get_docker_bridge_default_gateway()
            extra_flags.append(f'--dns={dns_server_ip}')
        super().start(mode=mode, allow_restart=allow_restart, rebuild=rebuild, hard=hard, show_print=show_print,
                      expose_port=expose_port, extra_flags=extra_flags,
                      docker_internal_env_vars=docker_internal_env_vars, run_env=run_env)
        if 'linux' in sys.platform.lower() and is_weave_up():
            try:
                self.connect_to_weave_network()
            except Exception as e:
                print(f'Cannot connect {self.container_name} to weave network: {e}')
