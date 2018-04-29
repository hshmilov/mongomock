import importlib
import os
import shutil
import subprocess
import sys

sys.path.append(os.path.join(os.path.abspath(__file__), '..'))

from utils import CORTEX_PATH, safe_run_bash, get_service
from services.plugin_service import PluginService

DEPLOYMENT_FOLDER_PATH = os.path.join(CORTEX_PATH, 'deployment')
VENV_WRAPPER = os.path.join(DEPLOYMENT_FOLDER_PATH, 'venv_wrapper.sh')
DEPLOY_DIR = os.path.abspath(os.path.join(CORTEX_PATH, 'deploy_artifacts'))
INSTALLER_PATH = os.path.join(DEPLOY_DIR, 'installer.py')
DEPLOY_CORTEX_DIR = os.path.join(DEPLOY_DIR, 'cortex')
AXONIUS_SH_PATH = os.path.join(DEPLOY_CORTEX_DIR, 'axonius.sh')
ADAPTERS = ['ad']
SERVICES = ['diagnostics']


def test_deployment():
    """
    We do here these procedures:
    1. Create a deployment path and call "make.py" to create an installation/upgrade package
    2. Delete all images, volumes, etc (super_clean()) but not sources (because we need them)
    3. Install the system, through the binary package we created in (1). This should be now independent
       and install the system regardless of anything that happened before in this step.
    4. Start services & adapters, note what is up, and insert credentials. Notice that we insert credentials from
       the original source code since the binary that we created is *production ready* and does include credentials or
       tests.
    5. Make an upgrade. This is done by the same binary package (we upgrade to the same version), just different params.
    6. Check that the upgrade succeeded (check that what was up is indeed up, but with different container id,
       and that the credentials are ok)
    """
    create_deploy_dir()
    make_installation()
    super_clean()
    install_first_time()
    start_services()
    start_adapters()
    first = check_is_up()
    insert_credentials()
    upgrade()
    second = check_is_up()
    assert_restarted(first, second)
    check_credentials()
    print_state('Done!')


def print_state(text):
    reset = '\033[00m'
    light_green = '\033[92m'
    print(f'{light_green}{text}{reset}')


def create_deploy_dir():
    print_state('Stage: Create empty dir for installation')
    if os.path.isdir(DEPLOY_DIR):
        shutil.rmtree(DEPLOY_DIR, ignore_errors=True)
    os.makedirs(DEPLOY_DIR)


def make_installation():
    print_state('Stage: Make installer')
    create_script_path = os.path.join(DEPLOYMENT_FOLDER_PATH, 'make.py')
    subprocess.check_call(safe_run_bash([VENV_WRAPPER, create_script_path, f'--out={INSTALLER_PATH}']))


def super_clean():
    print_state('Stage: Super clean')
    super_clean_script_path = os.path.join(CORTEX_PATH, 'devops', 'super_clean.sh')
    subprocess.check_call(safe_run_bash([super_clean_script_path]))


def install_first_time():
    print_state('Stage: Install --first-time')
    # no need for venv when installing using our installer
    subprocess.check_call(['python', INSTALLER_PATH, '--first-time'], cwd=DEPLOY_DIR)


def start_services():
    print_state(f'Stage: Start services {SERVICES}')
    for service in SERVICES:
        subprocess.check_call(safe_run_bash([AXONIUS_SH_PATH, 'service', service, 'up']))


def start_adapters():
    print_state(f'Stage: Start adapters {ADAPTERS}')
    for adapter in ADAPTERS:
        subprocess.check_call(safe_run_bash([AXONIUS_SH_PATH, 'adapter', adapter, 'up']))


def check_is_up():
    print_state('Stage: Checking status of adapters')
    axonius_system = get_service()
    ids = {}
    for service in axonius_system.axonius_services:
        assert service.is_up(), f'{service.__class__.__name__} is down'
        if isinstance(service, PluginService):
            ids[service.plugin_name] = service.get_container_id()
    for adapter_name in ADAPTERS:
        service = axonius_system.get_adapter(adapter_name)
        assert service.is_up(), f'adapter {adapter_name} is down'
        ids[service.plugin_name] = service.get_container_id()
    for service_name in SERVICES:
        service = axonius_system.get_plugin(service_name)
        assert service.is_up(), f'service {service_name} is down'
        if isinstance(service, PluginService):
            name = service.plugin_name
        else:
            name = service.__class__.__name__
        ids[name] = service.get_container_id()
    return ids


def insert_credentials():
    print_state('Stage: Insert credentials')
    axonius_system = get_service()
    for adapter in ADAPTERS:
        service = axonius_system.get_adapter(adapter)
        test_module = importlib.import_module(f'parallel_tests.test_{adapter}')
        test_class_name = f'Test{adapter.replace("_", " ").title().replace(" ", "_")}Adapter'
        test_class = getattr(test_module, test_class_name)
        test = test_class()
        some_client_details = test.some_client_details
        if isinstance(some_client_details, list):
            for client in some_client_details:
                service.add_client(client[0])
        else:
            service.add_client(some_client_details)
        assert service.clients(), f'Missing providers for {adapter}'


def upgrade():
    print_state('Stage: Upgrade')
    # no need for venv when installing using our installer
    subprocess.check_call(['python', INSTALLER_PATH], cwd=DEPLOY_DIR)


def assert_restarted(first, second):
    print_state('Stage: Assert restarted')
    for v in first:
        assert v in second, f'{v} has not been started after upgrade'
        assert first[v] != second[v], f'{v} has not been *re*started'
    for v in second:
        assert v in first, f'{v} has not been started before upgrade'


def check_credentials():
    print_state('Stage: Checking credentials')
    axonius_system = get_service()
    for adapter in ADAPTERS:
        service = axonius_system.get_adapter(adapter)
        assert service.clients(), f'Missing providers for {adapter}'
