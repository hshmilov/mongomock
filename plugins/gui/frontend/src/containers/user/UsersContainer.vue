<template>
    <x-page title="users">
        <x-data-query :module="module" :read-only="isReadOnly" />
        <x-data-table :module="module" id-field="internal_axon_id" title="Users" ref="table"
                      @click-row="configUser" v-model="isReadOnly? undefined: selectedUsers">
            <template slot="actions">
                <x-data-action-menu v-show="selectedUsers && selectedUsers.length" :module="module"
                                    :selected="selectedUsers" @done="updateUsers" />
                <!-- Modal for selecting fields to be presented in table, including adapter hierarchy -->
                <x-data-field-menu :module="module" />
                <div class="x-btn link" @click="exportCSV">Export CSV</div>
            </template>
        </x-data-table>
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xDataQuery from '../../components/data/DataQuery.vue'
    import xDataTable from '../../components/tables/DataTable.vue'
    import xDataFieldMenu from '../../components/data/DataFieldMenu.vue'
    import xDataActionMenu from '../../components/data/DataActionMenu.vue'

	import { mapState, mapActions } from 'vuex'
	import { FETCH_DATA_CONTENT_CSV } from '../../store/actions'

	export default {
		name: 'users-container',
        components: { xPage, xDataQuery, xDataTable, xDataFieldMenu, xDataActionMenu },
        computed: {
            ...mapState({
                isReadOnly(state) {
                    if (!state.auth.data || !state.auth.data.permissions) return true
                    return state.auth.data.permissions.Users === 'ReadOnly'
                },
                historicalState(state) {
                    return state[this.module].view.historical
                },
            }),
			module() {
				return 'users'
            }
        },
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

                let path = `${this.module}/${userId}`
                if (this.historicalState) {
				    path += `?history=${encodeURIComponent(this.historicalState)}`
                }
				this.$router.push({path: path})
			},
			exportCSV() {
				this.fetchContentCSV({ module: this.module })
			},
            updateUsers() {
				this.$refs.table.fetchContentPages()
				this.selectedUsers = []
            }
        }
    }
</script>

<style lang="scss">

</style>