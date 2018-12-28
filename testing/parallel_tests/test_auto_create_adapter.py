import codecs
import os

import pytest

from devops.scripts.automate_dev.create_adapter import get_action_table


def get_cortex_dir() -> str:
    """ Returns the relative path to cortex repo root directory """
    return os.path.relpath(os.path.join(os.path.dirname(__file__), '..', '..'))


def filename_for_test_generator():
    adapter_name = 'removethis'
    for filename in get_action_table(adapter_name).keys():
        filename = os.path.join(get_cortex_dir(), filename)

        while '{' in filename or adapter_name in filename:
            filename = os.path.split(filename)[0]
        yield filename


def test_paths():
    for filename in filename_for_test_generator():
        assert os.path.exists(filename), f'Filename {filename} is missing'


def is_valid_utf8(filename):
    try:
        f = codecs.open(filename, encoding='utf-8', errors='strict')
        for line in f:
            pass
        return True
    except UnicodeDecodeError:
        return False


def test_no_utf():
    for filename in filename_for_test_generator():
        if os.path.isfile(filename):
            assert is_valid_utf8(filename), 'fFilename {filename} contains non utf-8 chars'


@pytest.mark.skip(f'AX-2945')
def test_pylint():
    try:
        gitpylint = os.path.join(get_cortex_dir(), 'devops/scripts/git-pylint.sh')
        os.system('{path} asdf'.format(path=os.path.join(
            get_cortex_dir(), 'devops/scripts/automate_dev/create_adapter.py')))
        if not os.system(rf'{gitpylint} -P -d -o 2>&1 | tee /dev/stderr | grep -q "\[-\]"'):
            assert False, 'pylint failed!'
    finally:
        remove_generated_adapter('asdf')


def remove_generated_adapter(name):
    os.system('git checkout {path}'.format(path=os.path.join(get_cortex_dir(),
                                                             'plugins/gui/frontend/src/constants/plugin_meta.js')))
    os.system('git checkout {path}'.format(path=os.path.join(get_cortex_dir(),
                                                             'testing/services/ports.py')))
    os.system('rm -rf {path}'.format(path=os.path.join(get_cortex_dir(),
                                                       f'adapters/{name}_adapter/')))

    path_ = os.path.join(get_cortex_dir(), f'axonius-libs/src/libs/axonius-py/axonius/assets/logos/{name}_adapter.png')
    os.system('rm -rf {path}'.format(path=path_))
    os.system('rm -rf {path}'.format(path=os.path.join(get_cortex_dir(),
                                                       f'testing/parallel_tests/test_{name}.py')))
    os.system('rm -rf {path}'.format(path=os.path.join(get_cortex_dir(),
                                                       f'testing/services/adapters/{name}_service.py')))
    os.system('rm -rf {path}'.format(path=os.path.join(get_cortex_dir(),
                                                       f'rm -f testing/test_credentials/test_{name}_credentials.py')))
