from pymongo.collection import Collection
from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME

from ui_tests.tests.ui_test_base import TestBase


class TestLeftovers(TestBase):
    # https://axonius.atlassian.net/browse/AX-4431
    def test_leftovers(self):
        db = self.axonius_system.db.client
        configs_collection: Collection = db['core']['configs']
        deprecated_configs_collection: Collection = db['core']['configs_deprecated']

        # verify that the leftover is gone
        assert configs_collection.count_documents({
            PLUGIN_UNIQUE_NAME: 'reports_1234'
        }) == 0

        # verify that the leftover was safely moved
        assert deprecated_configs_collection.count_documents({
            PLUGIN_UNIQUE_NAME: 'reports_1234'
        }) == 1

        # verify that only the singleton remains
        assert configs_collection.count_documents({
            PLUGIN_NAME: 'reports'
        }) == 1

        # verify that the leftover db is gone
        assert db['reports_1234']['stuff_collection'].count_documents({}) == 0

        # verify that is was safely moved
        assert db['DEPRECATED_reports_1234']['stuff_collection'].count_documents({}) == 1
