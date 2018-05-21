<template>
    <x-page :breadcrumbs="[
    	{ title: 'adapters', path: { name: 'Adapters'}},
    	{ title: adapterName }
    ]" class="adapter-config">
            <div class="server-list-container">
                <div class="form-group">
                    <!-- Container for list of configured servers - both enabled and disabled -->
                    <div class="form-group-header">
                        <span class="form-group-title">Servers</span>
                    </div>
                    <dynamic-table v-if="schemaFields" :data="adapterClients" :fields="tableFields"
                                   add-new-data-label="Add a server" @select="configServer" @delete="deleteServer">
                    </dynamic-table>
                </div>
            </div>
            <tabs v-if="currentAdapter">
                <tab v-for="config, configName, i in currentAdapter.config_data" :key="i"
                     :title="config.schema.pretty_name || configName" :id="configName" :selected="!i">
                    <div class="configuration">
                        <x-schema-form :schema="config.schema" v-model="config.config" @validate="serverModal.valid = $event"/>
                        <a class="x-btn great" @click="saveConfig(configName, config.config)" tabindex="1">Save Config</a>
                    </div>
                </tab>
            </tabs>

            <modal v-if="serverModal.serverData && serverModal.uuid && serverModal.open"
                   class="server-config" @close="toggleServerModal" approve-text="save" @confirm="saveServer">
                <div slot="body">
                    <!-- Container for configuration of a single selected / added server -->
                    <x-logo-name :name="adapterPluginName" />
                    <div class="mt-3">
                        <div class="mb-2">Basic system credentials</div>
                        <x-schema-form :schema="adapterSchema" v-model="serverModal.serverData"
                                       :api-upload="`adapters/${adapterUniquePluginName}`"
                                       @submit="saveServer" @validate="serverModal.valid = $event"/>
                    </div>
                </div>
            </modal>
        <modal v-if="message">
            <div slot="body">
                <div class="show-space">{{message}}</div>
            </div>
            <button class="x-btn" slot="footer" @click="closeModal">OK</button>
        </modal>
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
	import DynamicTable from '../../components/tables/DynamicTable.vue'
	import Modal from '../../components/popover/Modal.vue'
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
	import Tabs from '../../components/tabs/Tabs.vue'
	import Tab from '../../components/tabs/Tab.vue'
    import xLogoName from '../../components/titles/LogoName.vue'
    import '../../components/icons/navigation'

	import { mapState, mapActions } from 'vuex'
	import {
		FETCH_ADAPTER_SERVERS, SAVE_ADAPTER_SERVER, ARCHIVE_SERVER
	} from '../../store/modules/adapter'
    import { pluginMeta } from '../../static.js'
    import {SAVE_PLUGIN_CONFIG} from "../../store/modules/configurable";

	export default {
		name: 'adapter-config-container',
		components: {Modal, xLogoName, Tabs, Tab, xPage, DynamicTable, xSchemaForm},
		computed: {
			...mapState(['adapter']),
			adapterUniquePluginName () {
				return this.$route.params.id
			},
            currentAdapter() {
			    return this.adapter.adapterList.data.find(x => x.unique_plugin_name == this.adapterUniquePluginName)
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
				},
                message: ''
			}
		},
		methods: {
			...mapActions({
				fetchAdapter: FETCH_ADAPTER_SERVERS,
				updateAdapterServer: SAVE_ADAPTER_SERVER,
                archiveServer: ARCHIVE_SERVER,
                updatePluginConfig: SAVE_PLUGIN_CONFIG
			}),
			returnToAdapters () {
				this.$router.push({name: 'Adapters'})
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
			},
            saveConfig(configName, config) {
                this.updatePluginConfig({
                    pluginId: this.adapterUniquePluginName,
                    configName: configName,
                    config: config
                }).then(() => this.message = 'Adapter Configuration Saved.')
            },
            closeModal() {
                this.message = ''
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
    .adapter-config {
        .server-list-container {
            .form-group-header {
                font-size: 20px;
                color: $theme-orange;
            }
        }
        .x-tabs {
            margin-top: 36px;
            .configuration {
                width: 600px;
                padding: 24px;
            }
        }
        .server-config {
            .form-group {
                padding-left: 12px;
            }
        }
    }
</style>