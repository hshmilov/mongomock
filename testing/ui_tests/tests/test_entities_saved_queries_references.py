from ui_tests.tests.ui_test_base import TestBase
from services.axonius_service import get_service
from axonius.plugin_base import EntityType


class TestEntitiesSavedQueriesReferences(TestBase):

    def test_saved_query_with_multiple_reference_levels(self):
        try:
            axonius_system = get_service()
            queries_tree = ['TEST A', 'TEST B', 'TEST C']

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            # Create 'tree'
            self.devices_page.create_base_query_for_reference(queries_tree[2])
            self.devices_page.create_saved_query_with_reference(queries_tree[1], [queries_tree[2]])
            self.devices_page.create_saved_query_with_reference(queries_tree[0], [queries_tree[1]])

            self.devices_page.execute_and_assert_query_reference(queries_tree[0], [queries_tree[1]])
            self.devices_page.execute_and_assert_query_reference(queries_tree[1], [queries_tree[2]])

            ids_map = {}
            queries = axonius_system.db.data.entity_views_collection[EntityType.Devices].find({
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

            # TEST A -> TEST B, # TEST A -> TEST C
            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[0]]
            }) == 2

            # TEST A -> TEST C, # TEST B -> TEST C
            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'target': ids_map[queries_tree[2]]
            }) == 2

        finally:
            self.devices_queries_page.switch_to_page()
            self.devices_queries_page.wait_for_table_to_be_responsive()
            self.devices_queries_page.check_queries_by_name(queries_tree)
            self.devices_queries_page.remove_selected_queries(True)
            axonius_system.clear_direct_references_collection(EntityType.Devices)

    def test_saved_query_change_reference(self):
        try:
            axonius_system = get_service()
            queries_tree = ['TEST A', 'TEST B', 'TEST C', 'TEST D']

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            # Create 'tree'
            self.devices_page.create_base_query_for_reference(queries_tree[2])
            self.devices_page.create_base_query_for_reference(queries_tree[3])
            self.devices_page.create_saved_query_with_reference(queries_tree[1], [queries_tree[2]])
            self.devices_page.create_saved_query_with_reference(queries_tree[0], [queries_tree[1]])

            self.devices_page.execute_and_assert_query_reference(queries_tree[0], [queries_tree[1]])
            self.devices_page.execute_and_assert_query_reference(queries_tree[1], [queries_tree[2]])

            # Change query reference, from B->C to B->D
            self.devices_page.execute_saved_query(queries_tree[1])
            self.devices_page.wait_for_table_to_be_responsive()
            self.devices_page.click_query_wizard()
            expressions = self.devices_page.find_expressions()
            self.devices_page.select_saved_query_reference(queries_tree[3], parent=expressions[0])
            self.devices_page.save_existing_query()
            self.devices_page.reset_query()

            self.devices_page.execute_saved_query(queries_tree[1])
            self.devices_page.wait_for_table_to_be_responsive()
            assert self.devices_page.get_table_count() == 1
            self.devices_page.click_query_wizard()
            expressions = self.devices_page.find_expressions()
            assert len(expressions) == 1
            assert self.devices_page.get_saved_query_value(parent=expressions[0]) == queries_tree[3]
            self.devices_page.close_dropdown()

            ids_map = {}
            queries = axonius_system.db.data.entity_views_collection[EntityType.Devices].find({
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
            }) == 0

            # TEST B -> TEST D
            assert axonius_system.entity_views_direct_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[1]],
                'target': ids_map[queries_tree[3]]
            }) == 1

            # TEST A -> TEST B, # TEST A -> TEST D
            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[0]],
                'target': ids_map[queries_tree[1]],
            }) == 1

            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[0]],
                'target': ids_map[queries_tree[3]],
            }) == 1

            # No one points to TEST C after the change.
            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'target': ids_map[queries_tree[2]],
            }) == 0

        finally:
            self.devices_queries_page.switch_to_page()
            self.devices_queries_page.wait_for_table_to_be_responsive()
            self.devices_queries_page.check_queries_by_name(queries_tree)
            self.devices_queries_page.remove_selected_queries(True)
            axonius_system.clear_direct_references_collection(EntityType.Devices)

    def test_saved_query_verify_safeguard(self):
        try:
            axonius_system = get_service()
            queries_tree = ['TEST A', 'TEST B', 'TEST C', 'TEST D']

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            # Create 'tree'
            self.devices_page.create_base_query_for_reference(queries_tree[3])
            self.devices_page.create_saved_query_with_reference(queries_tree[1], [queries_tree[3]])  # TEST B -> TEST D
            self.devices_page.create_saved_query_with_reference(queries_tree[2], [queries_tree[3]])  # TEST C -> TEST D
            self.devices_page.create_saved_query_with_reference(queries_tree[0], [queries_tree[1]])  # TEST A -> TEST B

            self.devices_queries_page.switch_to_page()
            self.devices_queries_page.wait_for_table_to_be_responsive()
            # B is referenced by A.
            self.devices_queries_page.check_queries_by_name([queries_tree[1]])
            self.devices_queries_page.remove_single_saved_query_with_safeguard()
            self.devices_queries_page.wait_for_table_to_be_responsive()
            # D is referenced by B,C.
            self.devices_queries_page.check_queries_by_name([queries_tree[0], queries_tree[2], queries_tree[3]])
            self.devices_queries_page.remove_multiple_saved_query_with_safeguard()
        finally:
            axonius_system.clear_direct_references_collection(EntityType.Devices)

    def test_saved_query_remove_with_references(self):
        try:
            axonius_system = get_service()
            queries_tree = ['TEST A', 'TEST B', 'TEST C']

            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            # Create 'tree'
            self.devices_page.create_base_query_for_reference(queries_tree[2])
            self.devices_page.create_saved_query_with_reference(queries_tree[1], [queries_tree[2]])
            self.devices_page.create_saved_query_with_reference(queries_tree[0], [queries_tree[1]])

            # Remove TEST B.
            self.devices_queries_page.switch_to_page()
            self.devices_queries_page.wait_for_table_to_be_responsive()
            # B is referenced by A.
            self.devices_queries_page.check_queries_by_name([queries_tree[1]])
            self.devices_queries_page.remove_single_saved_query_with_safeguard()

            ids_map = {}
            queries = axonius_system.db.data.entity_views_collection[EntityType.Devices].find({
                'query_type': 'saved',
                'name':  {
                    '$in': queries_tree
                }
            })
            for query in queries:
                query_id = str(query.get('_id'))
                name = query.get('name')
                ids_map[name] = query_id

                if name == 'TEST B':
                    assert query.get('archived')

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

            # TEST A -> TEST B, # TEST A -> TEST C
            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'origin': ids_map[queries_tree[0]]
            }) == 2

            # TEST A -> TEST C, # TEST B -> TEST C
            assert axonius_system.entity_views_indirect_references[EntityType.Devices].count_documents({
                'target': ids_map[queries_tree[2]]
            }) == 2

        finally:
            self.devices_queries_page.switch_to_page()
            self.devices_queries_page.wait_for_table_to_be_responsive()
            self.devices_queries_page.check_queries_by_name([queries_tree[0], queries_tree[2]])
            self.devices_queries_page.remove_selected_queries(True)
            axonius_system.clear_direct_references_collection(EntityType.Devices)
