<template>
    <x-page title="users">
        <x-data-query :module="module" />
        <x-data-table :module="module" v-model="selectedUsers" id-field="internal_axon_id" title="Users"
                      @click-row="configUser" ref="table">
            <template slot="actions">
                <x-data-action-menu v-show="selectedUsers && selectedUsers.length" :module="module"
                                    :selected="selectedUsers" @done="updateUsers" />
                <!-- Modal for selecting fields to be presented in table, including adapter hierarchy -->
                <x-data-field-menu :module="module" />
                <div class="x-btn link" @click="exportCSV">Export csv</div>
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

	import { mapActions } from 'vuex'
	import { FETCH_DATA_CONTENT_CSV } from '../../store/actions'

	export default {
		name: 'users-container',
        components: { xPage, xDataQuery, xDataTable, xDataFieldMenu, xDataActionMenu },
        computed: {
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

				this.$router.push({path: `${this.module}/${userId}`})
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