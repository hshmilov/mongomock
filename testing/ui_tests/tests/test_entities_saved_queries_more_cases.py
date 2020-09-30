from ui_tests.tests.ui_test_base import TestBase
from services.axonius_service import get_service
from axonius.plugin_base import EntityType


class TestEntitiesSavedQueriesMoreCases(TestBase):

    def test_saved_queries_circular_dependency(self):
        try:
            axonius_system = get_service()
            queries_tree = ['TEST A', 'TEST B', 'TEST C', 'TEST D', 'TEST E', 'TEST F']
            # A -> B -> C -> D
            #            \-> E -> F

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            # Create 'tree'
            self.devices_page.create_base_query_for_reference(queries_tree[3])
            self.devices_page.create_base_query_for_reference(queries_tree[5])
            self.devices_page.create_saved_query_with_reference(queries_tree[4], [queries_tree[5]])
            self.devices_page.create_saved_query_with_reference(queries_tree[2], [queries_tree[3], queries_tree[4]])
            self.devices_page.create_saved_query_with_reference(queries_tree[1], [queries_tree[2]])
            self.devices_page.create_saved_query_with_reference(queries_tree[0], [queries_tree[1]])

            self.devices_page.execute_and_assert_query_reference(queries_tree[0], [queries_tree[1]])
            self.devices_page.execute_and_assert_query_reference(queries_tree[1], [queries_tree[2]])
            self.devices_page.execute_and_assert_query_reference(queries_tree[2], [queries_tree[3], queries_tree[4]])

            # Execute E, and check that circle is not possible.
            self.devices_page.execute_saved_query(queries_tree[4])
            self.devices_page.wait_for_table_to_be_responsive()
            assert self.devices_page.get_table_count() == 1
            self.devices_page.click_query_wizard()
            expressions = self.devices_page.find_expressions()
            assert len(expressions) == 1
            options = self.devices_page.get_saved_queries_options(expressions[0])
            assert (queries_tree[0] not in options) and (queries_tree[1] not in options) and \
                   (queries_tree[2] not in options) and (queries_tree[3] in options)
            self.devices_page.close_dropdown()
            self.devices_page.close_dropdown()

            ids_map = {}
            queries = axonius_system.entity_views[EntityType.Devices].find({
                'query_type': 'saved',
                'name':  {
                    '$in': queries_tree
                }
            })
            for query in queries:
                query_id = str(query.get('_id'))
                name = query.get('name')
                ids_map[name] = query_id

            # TEST A -> TEST B
            assert axonius_system.entity_views_direct_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[0]],
                'target': ids_map[queries_tree[1]]
            }) == 1

            # TEST B -> TEST C
            assert axonius_system.entity_views_direct_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[1]],
                'target': ids_map[queries_tree[2]]
            }) == 1

            # TEST C -> TEST D / E
            assert axonius_system.entity_views_direct_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[2]]
            }) == 2

            # TEST C -> TEST D / E
            assert axonius_system.entity_views_direct_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[4]]
            }) == 1

            # A -> B, C, D, E ,F
            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[0]]
            }) == 5

            # B -> C, D, E , F
            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[1]]
            }) == 4

        finally:
            self.devices_queries_page.switch_to_page()
            self.devices_queries_page.check_queries_by_name(queries_tree)
            self.devices_queries_page.remove_selected_queries(True)
            axonius_system.clear_direct_references_collection(EntityType.Devices)
