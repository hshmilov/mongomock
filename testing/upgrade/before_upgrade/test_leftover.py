from pymongo.collection import Collection
from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME

from upgrade.UpgradeTestBase import UpgradeTestBase


class TestLeftovers(UpgradeTestBase):
    # https://axonius.atlassian.net/browse/AX-4431
    def test_leftovers(self):
        # Creating a fake 'leftover' plugin registration
        db = self.axonius_system.db.client
        configs_collection: Collection = db['core']['configs']
        reports_config = configs_collection.find_one({
            PLUGIN_NAME: 'reports'
        }, projection={
            '_id': False
        })
        assert reports_config is not None
        reports_config[PLUGIN_UNIQUE_NAME] = 'reports_1234'
        configs_collection.insert_one(reports_config)

        db['reports_1234']['stuff_collection'].insert_one({
            'test': 'test'
        })
