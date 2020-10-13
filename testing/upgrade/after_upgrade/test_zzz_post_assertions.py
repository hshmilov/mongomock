from upgrade.UpgradeTestBase import UpgradeTestBase


class TestZzzPostAssertions(UpgradeTestBase):
    def test_run_cycle_after_upgrade(self):
        self._clean_db()

        self.base_page.run_discovery()

        assert self.axonius_system.get_devices_db().count() > 0
        assert self.axonius_system.get_users_db().count() > 0

        assert len(list(self.axonius_system.get_devices_db().find({'$where': 'this.adapters.length > 1'}))) > 0
