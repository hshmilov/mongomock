<template>
    <x-page title="users">
        <x-data-query module="user" />
        <x-data-table module="user" v-model="selectedUsers" id-field="internal_axon_id" title="Users" @click-row="configUser">
            <template slot="actions">
                <x-data-action-menu v-show="selectedUsers && selectedUsers.length" module="user" :selected="selectedUsers" />
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
    import xDataActionMenu from '../../components/data/DataActionMenu.vue'

	import { mapActions } from 'vuex'
	import { FETCH_DATA_CONTENT_CSV } from '../../store/actions'

	export default {
		name: 'users-container',
        components: { xPage, xDataQuery, xDataTable, xDataViewMenu, xDataFieldMenu, xDataActionMenu },
        data() {
            return {
                selectedUsers: []
            }
        },
        methods: {
            ...mapActions({
				fetchContentCSV: FETCH_DATA_CONTENT_CSV
            }),
			configUser (userId) {
				if (this.selectedUsers && this.selectedUsers.length) return

				this.$router.push({path: `users/${userId}`})
			},
			exportCSV() {
				this.fetchContentCSV({ module: 'device' })
			}
        }
    }
</script>

<style lang="scss">

</style>