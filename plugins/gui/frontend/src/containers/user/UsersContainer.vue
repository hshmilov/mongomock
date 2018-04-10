<template>
    <x-page title="users">
        <x-data-query module="user" />
        <x-data-table module="user" id-field="internal_axon_id" title="Users">
            <template slot="actions">
                <x-data-view-menu module="user" />
                <!-- Modal for selecting fields to be presented in table, including adapter hierarchy -->
                <x-data-field-menu module="user" class="link" />
                <div class="link" @click="exportCSV">Export csv</div>
            </template>
        </x-data-table>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
    import xDataQuery from '../../components/data/DataQuery.vue'
    import xDataTable from '../../components/tables/DataTable.vue'
    import xDataViewMenu from '../../components/data/DataViewMenu.vue'
    import xDataFieldMenu from '../../components/data/DataFieldMenu.vue'

	import { mapState, mapActions } from 'vuex'
    import { FETCH_DATA_FIELDS, FETCH_DATA_CONTENT_CSV } from '../../store/actions'

	export default {
		name: 'users-container',
        components: { xPage, xDataQuery, xDataTable, xDataViewMenu, xDataFieldMenu },
        computed: {
            ...mapState(['user', 'adapter'])
        },
        data() {
			return {
			    selectedUsers: []
            }
        },
        methods: {
            ...mapActions({
                fetchFields: FETCH_DATA_FIELDS,
				fetchContentCSV: FETCH_DATA_CONTENT_CSV
            }),
			exportCSV() {
				this.fetchContentCSV({ module: 'device' })
			}
        },
        created() {
            this.fetchFields({module: 'user'})
        }
	}
</script>

<style lang="scss">

</style>