import json
from pathlib import Path

from system_consts import CORTEX_PATH, CUSTOMER_CONF_RELATIVE_PATH
from exclude_helper import EXCLUDE_LIST_KEY, ADD_TO_EXCLUDE_KEY, REMOVE_FROM_EXCLUDE_KEY
from ui_tests.tests.ui_test_base import TestBase


class TestPerCustomerSettings(TestBase):
    # pylint: disable=no-self-use
    def test_add_nimbul(self):
        with_nimbul = {
            EXCLUDE_LIST_KEY: {
                ADD_TO_EXCLUDE_KEY: [],
                REMOVE_FROM_EXCLUDE_KEY: ['nimbul']
            }
        }

        path = Path(CORTEX_PATH) / 'install_dir' / 'cortex' / CUSTOMER_CONF_RELATIVE_PATH
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(json.dumps(with_nimbul))
