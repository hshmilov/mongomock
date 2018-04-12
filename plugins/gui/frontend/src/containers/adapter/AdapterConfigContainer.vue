<template>
    <x-page :breadcrumbs="[
    	{ title: 'adapters', path: { name: 'Adapters'}},
    	{ title: adapterName }
    ]">
            <div class="server-list-container row">
                <div class="form-group">
                    <!-- Container for list of configured servers - both enabled and disabled -->
                    <div class="form-group-header">
                        <svg-icon name="navigation/device" width="24" height="24" :original="true"></svg-icon>
                        <span class="form-group-title">Add / update Servers</span>
                    </div>
                    <dynamic-table v-if="schemaFields" :data="adapterClients" :fields="tableFields" class="mt-3"
                                   add-new-data-label="Add a server" @select="configServer" @delete="deleteServer">
                    </dynamic-table>
                </div>
            </div>
            <div class="row">
                <div class="form-group place-right">
                    <a class="btn btn-inverse" @click="returnToAdapters">back</a>
                </div>
            </div>
            <modal v-if="serverModal.serverData && serverModal.uuid && serverModal.open"
                   class="config-server" @close="toggleServerModal" approve-text="save" @confirm="saveServer">
                <div slot="body">
                    <!-- Container for configuration of a single selected / added server -->
                    <status-icon-logo-text :logoValue="adapterPluginName" status-icon-value="empty"
                                           :textValue="serverModal.serverName" />
                    <div class="mt-3">
                        <div class="mb-2">Basic system credentials</div>
                        <x-schema-form :schema="adapterSchema" v-model="serverModal.serverData"
                                       @submit="saveServer" @validate="serverModal.valid = $event"/>
                    </div>
                </div>
            </modal>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import DynamicTable from '../../components/tables/DynamicTable.vue'
	import GenericForm from '../../components/GenericForm.vue'
	import StatusIconLogoText from '../../components/StatusIconLogoText.vue'
	import Modal from '../../components/popover/Modal.vue'
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
	import '../../components/icons/navigation'

	import { mapState, mapActions } from 'vuex'
	import {
		FETCH_ADAPTER_SERVERS, SAVE_ADAPTER_SERVER, ARCHIVE_SERVER
	} from '../../store/modules/adapter'
    import { pluginMeta } from '../../static.js'

	export default {
		name: 'adapter-config-container',
		components: {Modal, StatusIconLogoText, GenericForm, xPage, DynamicTable, xSchemaForm},
		computed: {
			...mapState(['adapter']),
			adapterUniquePluginName () {
				return this.$route.params.id
			},
			adapterPluginName () {
				return this.adapterUniquePluginName.match(/(.*_adapter)_\d*/)[1]
			},
			adapterName () {
				if (!pluginMeta[this.adapterPluginName]) { return this.adapterPluginName }
				return pluginMeta[this.adapterPluginName].title
			},
			adapterData () {
				return this.adapter.currentAdapter.data
			},
            adapterClients () {
				return this.adapterData.clients.map((client) => {
					return {
						id: client.uuid,
						status: client.status,
                        ...client.client_config,
                        error: client.error
                    }
                })
            },
            adapterSchema () {
				return this.adapterData.schema
            },
			schemaFields () {
				if (!this.adapterSchema) { return }
				return this.adapterSchema.items.map((schemaField) => {
					let field = {
						path: schemaField.name, name: schemaField.title || schemaField.name, control: schemaField.type,
						type: schemaField.type
					}
					if (schemaField.format && schemaField.format === 'password') {
						field.hidden = true
					} else if (field.control === 'string') {
						field.control = 'text'
                        field.type = 'text'
					} else if (field.control === 'array') {
						field.type = 'file'
                    }
                    return field
				})
			},
            tableFields () {
				return [
					{path: 'status', name: '', type: 'status'},
                    ...this.schemaFields,
                    {path: 'error', name: 'Error', control: 'text', type: 'error'}
                ]
            }
		},
		data () {
			return {
				serverModal: {
					open: false,
					serverData: {},
                    serverName: 'New Server',
                    uuid: null,
                    valid: true
				}
			}
		},
		methods: {
			...mapActions({
				fetchAdapter: FETCH_ADAPTER_SERVERS,
				updateAdapterServer: SAVE_ADAPTER_SERVER,
                archiveServer: ARCHIVE_SERVER
			}),
			returnToAdapters () {
				this.$router.push({name: 'Adapters'})
			},
			saveAdapter () {
				/* Validation */

				/* Save and return to adapters page */
//				this.updateAdapter(this.adapterData)
				this.returnToAdapters()
			},
			configServer (serverId) {
				this.serverModal.valid = true
				if (serverId === 'new') {
					this.serverModal.serverData = {}
					this.serverModal.serverName = 'New Server'
					this.serverModal.uuid = serverId
				} else {
					this.adapterData.clients.forEach((server, index) => {
						if (server.uuid === serverId) {
							this.serverModal.serverData = { ...server['client_config'] }
							this.serverModal.serverName = server['client_id']
                            this.serverModal.uuid = server.uuid
						}
					})
				}
				this.toggleServerModal()
			},
			deleteServer (serverId) {
                this.archiveServer({
                    adapterId: this.adapterUniquePluginName,
                    serverId: serverId
                })
			},
			saveServer () {
				if (!this.serverModal.valid) {
					return
                }
				this.updateAdapterServer({
					adapterId: this.adapterUniquePluginName,
					serverData: this.serverModal.serverData,
                    uuid: this.serverModal.uuid
				})
				this.toggleServerModal()
			},
			toggleServerModal () {
				this.serverModal.open = !this.serverModal.open
			}
		},
		created () {
			/*
                If no adapter mapped controls source, or has wrong id for current adapter selection,
                try and fetch it (happens after refresh) and update local adapter
             */
			if (!this.adapterData || !this.adapterData.schema) {
				this.fetchAdapter(this.$route.params.id)
			}
		}
	}
</script>

<style lang="scss">
    .config-server {
        .form-group {
            padding-left: 12px;
        }
    }
</style>