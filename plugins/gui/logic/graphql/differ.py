"""
Main logic

    - Extract _compatibilityAPI O(n)
    - Compare count O(1)
    - Sort Both by internal axon id 2 * O(nlogn)
    - Compare O(n) + n*O(k)

mr = json.load(open("test_data/golden_mongo.json"))
br = json.load(open("test_data/golden_pg.json"))

Differ().query_difference(br, mr)

"""
import logging
import logging.handlers
import os
from datetime import datetime

from dateutil.parser import parse

from axonius.logging.customised_json_formatter import CustomisedJSONFormatter
from axonius.logging.logger import BYTES_LIMIT
from axonius.plugin_base import LOG_PATH


# pylint: disable=C0103, R0911, R1710


def create_diff_logger():
    c_logger = logging.getLogger('differ')
    # Creating a rotating file log handler
    regular_log_path = os.path.join(LOG_PATH, f'differ.axonius.log')
    file_handler = logging.handlers.RotatingFileHandler(regular_log_path,
                                                        maxBytes=BYTES_LIMIT,
                                                        backupCount=3)
    file_handler.setFormatter(CustomisedJSONFormatter('differ'))
    c_logger.addHandler(file_handler)
    c_logger.setLevel(logging.DEBUG)
    return c_logger


class DiffException(Exception):
    pass


SORT_KEY = 'internal_axon_id'

EMPTY = [[None], '', None, 'Unknown', 0]

SKIP_KEY = ['meta_data.client_used', 'adapters_details']

logger = create_diff_logger()
logger.info('bandicoot differ initialized logger')


class Differ:
    """
    Differ is a simple class to compare results from mongo and bandicoot, this code should be a temporary check
    that the data is the same, in future releases this whole part should be removed and the FE should query the
    bandicoot endpoint API
    """

    def query_difference(self, bandicoot_result, mongo_result):
        """
        Compares to query results
        """
        logger.info('Started bandicoot query difference')
        # extract compatibility api from the bandicoot result
        r = [i['_compatibilityAPI'] for i in bandicoot_result['data']['devices']]

        if len(r) != len(mongo_result):
            logger.warning(f'Bandicoot compare: Count result mismatch')
            return False
        # sort by axonius id
        sb = sorted(r, key=lambda i: i[SORT_KEY])
        sm = sorted(mongo_result, key=lambda i: i[SORT_KEY])

        result = True
        # always compare all to find max mismatch, return fail if even one compare was wrong
        for b, m in zip(sb, sm):
            if b[SORT_KEY] != m[SORT_KEY]:
                logger.warning(f'Missing axon device: {b[SORT_KEY]}')
                continue
            if self.compare_devices(b, m):
                result = False
        return result

    def compare_devices(self, b_device: dict, m_device: dict):
        """
        Compare two devices
        Args:
            b_device: device as received from bandicoot
            m_device: device as received from mongo

        Returns:
            whether devices are the same or not.
        """
        result = True
        for k, v in m_device.items():

            if k in SKIP_KEY:
                continue

            if k not in b_device:
                if v in EMPTY:
                    continue
                logger.debug(f'Missing key {k}: {v}')
                continue

            b_value = b_device[k]
            if m_device['adapter_list_length'] == 1 and k.endswith('details') and isinstance(b_value, list):
                b_value = b_value[0]

            if not self.compare_values(v, b_value):
                logger.warning(f'id: {m_device[SORT_KEY]}\nKey: {k}\nValue mismatch {v} != {b_device[k]}\n')
                result = False

        return result

    def compare_dicts(self, d1: dict, d2: dict):
        for k, v in d1.items():
            if k in SKIP_KEY:
                continue

            if k not in d2:
                if v in EMPTY:
                    continue
                return False

            if not self.compare_values(v, d2[k]):
                return False

    def compare_values(self, v1, v2):
        """
        Compare two values in multiple scenarios based on thier type.
        """
        # simple compare
        if v1 == v2:
            return True
        # if both values are one of the possible empty values
        if v1 in EMPTY and v2 in EMPTY:
            return True

        if isinstance(v1, dict) and isinstance(v2, dict):
            return self.compare_dicts(v1, v2)

        if isinstance(v1, list) and isinstance(v2, list):
            return self.compare_lists(v1, v2)
        # if one item is a list of length one and the other is a simple value (not a list)
        # extract the oen from the list happens in array types, for example 1 == [1].
        if isinstance(v1, list) and not isinstance(v2, list) and len(v1) == 1:
            return self.compare_values(v1[0], v2)
        # same as above but the opposite
        if isinstance(v2, list) and not isinstance(v1, list) and len(v2) == 1:
            return self.compare_values(v1, v2[0])

        if isinstance(v1, str) and isinstance(v2, str):
            return self.compare_strings(v1, v2)
        # datetime == epoch
        if isinstance(v1, datetime) and isinstance(v2, (float, int)):
            return v1.timestamp() * 1000 == v2
        # date str == epoch
        if isinstance(v1, str) and self.is_date(v1) and isinstance(v2, int):
            return parse(v1).timestamp() * 1000 == v2
        # epoch == date_str
        if isinstance(v2, str) and self.is_date(v2) and isinstance(v1, int):
            return parse(v2).timestamp() * 1000 == v1

        return False

    def compare_lists(self, l1, l2):
        l1, l2 = sorted(set(l1)), sorted(set(l2))
        for i, j in zip(l1, l2):
            if self.compare_values(i, j):
                continue
            return False
        return True

    @staticmethod
    def compare_strings(s1, s2):
        return s1.lower() == s2.lower()

    @staticmethod
    def is_date(s):
        try:
            parse(s)
            return True
        except ValueError:
            return False
