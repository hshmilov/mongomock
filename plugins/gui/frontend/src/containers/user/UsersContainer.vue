<template>
    <x-page title="users">
        <x-data-query module="user" />
        <x-data-table module="user" v-model="selectedUsers" id-field="internal_axon_id" title="Users">
            <template slot="actions">
                <x-data-view-menu module="user" />
                <!-- Modal for selecting fields to be presented in table, including adapter hierarchy -->
                <x-data-field-menu module="user" class="link" />
                <div class="link" @click="exportCSV">Export csv</div>
                <div v-if="selectedUsers.length" class="link" @click="activate(disable_users)">Disable Users</div>
            </template>
        </x-data-table>
        <feedback-modal v-model="disable_users.isActive"
                        :handleSave="saveDisableUsers"
                        message="Disable users">
            <div>Out of {{selectedUsers.length}} users, {{disabelableUsers.length}} are disabelable.</div>
            <div>These users will not appear in further scans.</div>
            <div>Are you sure you want to continue?</div>
        </feedback-modal>
    </x-page>
</template>

<script>
    import xPage from '../../components/layout/Page.vue'
    import xDataQuery from '../../components/data/DataQuery.vue'
    import xDataTable from '../../components/tables/DataTable.vue'
    import xDataViewMenu from '../../components/data/DataViewMenu.vue'
    import xDataFieldMenu from '../../components/data/DataFieldMenu.vue'
    import FeedbackModal from '../../components/popover/FeedbackModal.vue'

	import { mapState, mapActions } from 'vuex'
    import { DISABLE_USERS } from '../../store/modules/user'
	import { FETCH_DATA_CONTENT_CSV } from '../../store/actions'

	export default {
		name: 'users-container',
        components: { xPage, xDataQuery, xDataTable, xDataViewMenu, xDataFieldMenu, FeedbackModal },
        computed: {
            ...mapState(['user', 'adapter']),
            userById() {
                if (!this.user.data.content.data || !this.user.data.content.data.length) return {}

                return this.user.data.content.data.filter((user) => {
                    return this.selectedUsers.includes(user.internal_axon_id)
                }).reduce(function (map, input) {
                    map[input.internal_axon_id] = input
                    return map
                }, {})
            },
            adaptersByUniquePluginName() {
                if (!this.adapter || !this.adapter.adapterList) return {}
                return this.adapter.adapterList.data.reduce((map, input) => {
                    map[input.unique_plugin_name] = input
                    return map
                }, {})
            },
            disabelableUsers() {
                return Object.values(this.userById).filter(user => {
                    var user_adapters = user.unique_adapter_names.map(adapter => this.adaptersByUniquePluginName[adapter])
                    return user_adapters.some(adapter => adapter && adapter.supported_features.includes("Userdisabelable"))
                })
            }
        },
        data() {
            return {
                selectedUsers: [],
                disable_users: {
                    isActive: false
                },
            }
        },
        methods: {
            ...mapActions({
				fetchContentCSV: FETCH_DATA_CONTENT_CSV,
                disableUsers: DISABLE_USERS
            }),
            activate(module) {
                module.isActive = true
                // Close the actions dropdown
                this.$el.click()
            },
            saveDisableUsers() {
                return this.disableUsers(this.disabelableUsers.map(x => x.internal_axon_id))
            },
			exportCSV() {
				this.fetchContentCSV({ module: 'device' })
			}
        }
    }
</script>

<style lang="scss">

</style>