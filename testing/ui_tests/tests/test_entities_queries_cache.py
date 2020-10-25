import time

from ui_tests.tests.ui_test_base import TestBase
from services.axonius_service import get_service


class TestEntitiesQueriesCache(TestBase):

    def _assert_results_count(self, count: int):
        assert self.devices_page.count_entities() == count
        assert len(self.devices_page.get_all_table_rows()) == count

    def test_entities_queries_cache_change(self):
        try:
            self.settings_page.toggle_queries_cache()
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            self.devices_page.query_hostname_contains('dc')
            self.devices_page.wait_for_table_to_be_responsive()
            self._assert_results_count(7)

            # Make sure same results returned.
            self.settings_page.switch_to_page()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            self._assert_results_count(7)

            devices_db = get_service().get_devices_db()
            devices_count = devices_db.count_documents({})
            assert devices_count > 0
            existing_doc = devices_db.find_one({
                'adapters.plugin_name': 'active_directory_adapter',
                'adapters.data.name': 'DC1'
            })

            del existing_doc['_id']
            existing_doc['internal_axon_id'] = existing_doc['internal_axon_id'] + '_tmp'
            existing_doc['adapters'][0]['data']['id'] = existing_doc['adapters'][0]['data']['id'] + '_tmp'
            existing_doc['adapters'][0]['quick_id'] = existing_doc['adapters'][0]['quick_id'] + '_tmp'
            existing_doc['adapters'][0]['data']['name'] = 'DC1_tmp'
            devices_db.insert_one(existing_doc)

            assert devices_db.count_documents({}) == devices_count + 1

            # Without cleaning the cache, nothing should change.
            self.settings_page.switch_to_page()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            self._assert_results_count(7)

            # After clash clean, we should get the latest result.
            self.devices_page.reset_queries_cache()
            self.devices_page.wait_for_table_to_be_responsive()
            self._assert_results_count(8)

            self.devices_page.reset_query()
            self.settings_page.switch_to_page()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            self.devices_page.query_hostname_contains('dc')
            self.devices_page.wait_for_table_to_be_responsive()
            # Make sure new results are returned.
            self._assert_results_count(8)

        finally:
            self.settings_page.toggle_queries_cache(make_yes=False)
            self.settings_page.toggle_auto_querying(make_yes=True)

    def test_entities_queries_cache_last_update(self):
        try:
            self.settings_page.toggle_queries_cache()
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            self.devices_page.query_hostname_contains('dc')
            self.devices_page.wait_for_table_to_be_responsive()
            self._assert_results_count(7)
            initial_datetime_object = self.devices_page.get_query_cache_last_updated()

            # Make sure same results returned.
            self.settings_page.switch_to_page()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            self._assert_results_count(7)
            datetime_object = self.devices_page.get_query_cache_last_updated()

            print(initial_datetime_object.hour)
            print(initial_datetime_object.minute)
            assert initial_datetime_object.hour == datetime_object.hour
            assert initial_datetime_object.minute == datetime_object.minute

        finally:
            self.settings_page.toggle_queries_cache(make_yes=False)
            self.settings_page.toggle_auto_querying(make_yes=True)

    def test_entities_queries_cache_ttl_expiration(self):
        try:
            pattern = 'ENTITIES_CACHE_devices_*'
            axonius_service = get_service()
            axonius_service.flush_redis_entities_cache()
            assert len(axonius_service.get_cache_entries_with_pattern(pattern)) == 0
            self.settings_page.toggle_queries_cache(ttl=1)  # 1 minute ttl.

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            self.devices_page.query_hostname_contains('dc')
            self.devices_page.wait_for_table_to_be_responsive()
            self._assert_results_count(7)
            self.settings_page.switch_to_page()

            # one for empty AQL and one for 'dc' query. (for each key, a :TIME key is inserted as well)
            assert len(axonius_service.get_cache_entries_with_pattern(pattern)) == 4

            time.sleep(60)
            assert len(axonius_service.get_cache_entries_with_pattern(pattern)) == 0

        finally:
            self.settings_page.toggle_queries_cache(make_yes=False)
            self.settings_page.toggle_auto_querying(make_yes=True)
