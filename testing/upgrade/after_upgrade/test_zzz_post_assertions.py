from axonius.entities import EntityType
from ui_tests.tests.ui_test_base import TestBase


class TestZzzPostAssertions(TestBase):
    def test_run_cycle_after_upgrade(self):
        self.axonius_system.get_devices_db().remove()
        self.axonius_system.get_users_db().remove()
        self.axonius_system.db.get_entity_db_view(EntityType.Users).remove()
        self.axonius_system.db.get_entity_db_view(EntityType.Devices).remove()

        self.base_page.run_discovery()

        assert self.axonius_system.get_devices_db().count() > 0
        assert self.axonius_system.get_users_db().count() > 0

        assert len(list(self.axonius_system.get_devices_db().find({'$where': 'this.adapters.length > 1'}))) > 0
