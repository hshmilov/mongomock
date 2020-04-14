import docker

from retrying import retry

from axonius.consts.plugin_consts import MASTER_PROXY_PLUGIN_NAME
from services.ports import DOCKER_PORTS
from ui_tests.tests.instances_test_base import TestInstancesBase


class TestInstanceMasterDockerRestart(TestInstancesBase):

    def test_instances_after_master_docker_restart(self):
        self.put_customer_conf_file()

        self.join_node()

        # restart docker service and terminate master-node conn
        environment = {'DOCKER_HOST': 'unix:///var/run/weave/weave.sock'}
        client = docker.from_env(environment=environment)
        master_proxy = client.containers.get(MASTER_PROXY_PLUGIN_NAME)
        master_proxy.restart()

        self.check_proxy_tunnel()

    def check_proxy_tunnel(self):
        self.check_master_proxy()

    @retry(stop_max_attempt_number=60,
           wait_fixed=10000)
    def check_master_proxy(self):
        instance = self._instances[0]
        self.logger.info(f'Checking if master proxy works')
        port = DOCKER_PORTS[MASTER_PROXY_PLUGIN_NAME]
        rc, out = instance.ssh(f'export https_proxy=https://localhost:{port} && curl https://manage.chef.io')
        if rc != 0:
            self.logger.info(f'proxy failed: {out}')
        assert rc == 0
