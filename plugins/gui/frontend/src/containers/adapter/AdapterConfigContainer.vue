<template>
    <x-page :breadcrumbs="[
    	{ title: 'adapters', path: { name: 'Adapters'}},
    	{ title: adapterName }
    ]" class="adapter-config">
        <x-table-actions title="Add or Edit Servers" :loading="loading">
            <template slot="actions">
                <div v-if="selectedServers && selectedServers.length" @click="removeServers" class="x-btn link">Remove</div>
                <div @click="configServer('new')" id="new_server" class="x-btn">+ New Server</div>
            </template>
            <x-table slot="table" :fields="tableFields" :data="adapterClients" :click-row-handler="configServer"
                     id-field="uuid" v-model="selectedServers" />
        </x-table-actions>

        <div class="config-settings">
            <div class="header x-btn link" @click="toggleSettings">
                <svg-icon name="navigation/settings" :original="true" height="20"/>Advanced Settings</div>
            <div class="content">
                <tabs v-if="currentAdapter && advancedSettings" class="growing-y" ref="tabs">
                    <tab v-for="config, configName, i in currentAdapter.config" :key="i"
                         :title="config.schema.pretty_name || configName" :id="configName" :selected="!i">
                        <div class="configuration">
                            <x-schema-form :schema="config.schema" v-model="config.config" @validate="validateConfig"/>
                            <a @click="saveConfig(configName, config.config)" tabindex="1"
                               class="x-btn" :class="{disabled: !configValid}">Save Config</a>
                        </div>
                    </tab>
                </tabs>
            </div>
        </div>

        <modal v-if="serverModal.serverData && serverModal.uuid && serverModal.open" size="lg" class="config-server"
               @close="toggleServerModal" @confirm="saveServer" @enter="promptSaveServer">
            <div slot="body">
                <!-- Container for configuration of a single selected / added server -->
                <x-logo-name :name="adapterPluginName" :title="adapterName" />
                <div class="server-error" v-if="serverModal.error">
                    <svg-icon name="symbol/error" :original="true" height="12"></svg-icon>
                    <div class="error-text">{{serverModal.error}}</div>
                </div>
                <x-schema-form :schema="adapterSchema" v-model="serverModal.serverData" @submit="saveServer"
                               @validate="validateServer" :api-upload="`adapters/${adapterId}`" />
            </div>import aiohttp
            <template slot="footer">
                <button @click="toggleServerModal" class="x-btn link">Cancel</button>
                <button id="test_reachability" @click="testServer" class="x-btn" :class="{disabled: !serverModal.valid}">Test Connectivity</button>
                <button id="save_server" @click="saveServer" class="x-btn" :class="{disabled: !serverModal.valid}">Save</button>
            </template>
        </modal>
        <modal v-if="deleting" @close="closeConfirmDelete" @confirm="doRemoveServers" approve-text="Delete">
            <div slot="body">Are you sure you want to delete this server? <br/><br/>
                <input type="checkbox" id="deleteEntitiesCheckbox" v-model="deleteEntities">
                <label for="deleteEntitiesCheckbox">Also delete all associated entities (devices, users)</label>
            </div>
        </modal>
        <x-toast v-if="message" :message="message" @done="removeToast" :timed="false" />
    </x-page>
</template>

<script>
	import xPage from '../../components/layout/Page.vue'
    import xTableActions from '../../components/tables/ActionableTable.vue'
    import xTable from '../../components/schema/SchemaTable.vue'
	import Modal from '../../components/popover/Modal.vue'
    import xSchemaForm from '../../components/schema/SchemaForm.vue'
	import Tabs from '../../components/tabs/Tabs.vue'
	import Tab from '../../components/tabs/Tab.vue'
    import xLogoName from '../../components/titles/LogoName.vue'
    import xToast from '../../components/popover/Toast.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
	import {
		FETCH_ADAPTERS, UPDATE_CURRENT_ADAPTER, SAVE_ADAPTER_SERVER, ARCHIVE_SERVER, TEST_ADAPTER_SERVER
	} from '../../store/modules/adapter'
    import { pluginMeta } from '../../constants/plugin_meta.js'
    import { SAVE_PLUGIN_CONFIG } from "../../store/modules/configurable"
	import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

	export default {
		name: 'adapter-config-container',
		components: { xPage, xTableActions, xTable, Tabs, Tab, Modal, xLogoName, xSchemaForm, xToast },
		computed: {
			...mapState({
                currentAdapter(state) {
					return state.adapter.currentAdapter
                }
			}),
			adapterId () {
				return this.$route.params.id
			},
			adapterPluginName () {
				return this.adapterId.match(/(.*_adapter)_\d*/)[1]
			},
			adapterName () {
				if (!pluginMeta[this.adapterPluginName]) { return this.adapterPluginName }
				return pluginMeta[this.adapterPluginName].title
			},
            adapterClients () {
				if (!this.currentAdapter || !this.currentAdapter.clients) return []
				return this.currentAdapter.clients.map((client) => {
					return {
						uuid: client.uuid,
						status: client.status,
                        ...client.client_config,
                        error: client.error
                    }
                })
            },
            adapterSchema () {
				if (!this.currentAdapter) return null
				return this.currentAdapter.schema
            },
            tableFields () {
				if (!this.adapterSchema || !this.adapterSchema.items) return []
				return [
					{ name: 'status', title: '', type: 'string', format: 'icon' },
                    ...this.adapterSchema.items.filter(field => (field.type !== 'file' && field.format !== 'password')),
                ]
            }
		},
		data () {
			return {
				loading: false,
				serverModal: {
					open: false,
					serverData: {},
                    error: '',
                    serverName: 'New Server',
                    uuid: null,
                    valid: false
				},
                selectedServers: [],
                message: '',
                advancedSettings: false,
                configValid: true,
                deleting: false,        // whether or not the modal for deleting confirmation is displayed
                deleteEntities: false,  // if 'deleting = true' and deleting was confirmed this means that
                                        // also the entities of the associated users should be deleted
			}
		},
		methods: {
            ...mapMutations({ updateAdapter: UPDATE_CURRENT_ADAPTER, changeState: CHANGE_TOUR_STATE }),
			...mapActions({
                fetchAdapters: FETCH_ADAPTERS, updateServer: SAVE_ADAPTER_SERVER, testAdapter: TEST_ADAPTER_SERVER,
                archiveServer: ARCHIVE_SERVER, updatePluginConfig: SAVE_PLUGIN_CONFIG
			}),
			configServer (serverId) {
            	this.message = ''
				this.serverModal.valid = true
				if (serverId === 'new') {
					this.serverModal = { ...this.serverModal,
                        serverData: {}, serverName: 'New Server', uuid: serverId, error: '', valid: false }
				} else {
					let server = this.currentAdapter.clients.find(server => (server.uuid === serverId))
                    this.serverModal = { ...this.serverModal,
                        serverData: { ...server.client_config }, serverName: server.client_id,
                        uuid: server.uuid, error: server.error, valid: true
                    }
				}
				this.toggleServerModal()
			},
            promptSaveServer() {
				this.changeState({name: 'saveServer'})
            },
			removeServers () {
                this.deleting = true
			},
            doRemoveServers() {
                this.selectedServers.forEach(serverId => this.archiveServer({
					adapterId: this.adapterId,
					serverId: serverId,
                    deleteEntities: this.deleteEntities
				}))
                this.selectedServers = []
                this.deleting = false
            },
            closeConfirmDelete() {
                this.deleting = false
                this.deleteEntities = false
            },
            validateServer(valid) {
            	this.serverModal.valid = valid
            },
			saveServer () {
				if (!this.serverModal.valid) {
					return
                }
                this.message = 'Connecting to Server...'
				this.updateServer({
					adapterId: this.adapterId,
					serverData: this.serverModal.serverData,
                    uuid: this.serverModal.uuid
				}).then((updateRes) => {
					this.fetchAdapters().then(() => {
                        document.getElementById(updateRes.data.id).children[2].id = 'status_server'
						this.changeState({name: `${updateRes.data.status}Server`})
                        if (updateRes.data.status === 'error') {
                        	this.message = 'Problem connecting. Review error and try again.'
						} else {
                        	this.message = 'Connection established. Data collection initiated...'
						}
					})
				})
				this.toggleServerModal()
			},
            testServer () {
                if (!this.serverModal.valid) {
                    return
                }
                this.message = 'Testing server Connection...'
                this.testAdapter({
                    adapterId: this.adapterId,
                    serverData: this.serverModal.serverData,
                    uuid: this.serverModal.uuid
                }).then((updateRes) => {
                    this.fetchAdapters().then(() => {
                        if (updateRes.data.status === 'error') {
                            this.message = 'Problem connecting to server.'
                        } else {
                            this.message = 'Connection is valid.'
                        }
                    })
                })
            },
			toggleServerModal () {
				this.serverModal.open = !this.serverModal.open
			},
            validateConfig(valid) {
            	this.configValid = valid
            },
            saveConfig(configName, config) {
                this.updatePluginConfig({
                    pluginId: this.adapterId,
                    configName: configName,
                    config: config
                }).then(() => this.message = 'Adapter configuration saved.')
            },
            removeToast() {
                this.message = ''
            },
            toggleSettings() {
                if (this.advancedSettings) {
            		this.$refs.tabs.$el.classList.add('shrinking-y')
                    setTimeout(() => this.advancedSettings = false, 1000)
                } else {
            	    this.advancedSettings = true
                }
            }
		},
		created () {
			if (!this.currentAdapter || this.currentAdapter.id !== this.adapterId) {
				this.loading = true
            }
			this.fetchAdapters().then(() => {
                this.updateAdapter(this.adapterId)
                this.loading = false
            })
			this.changeState({name: 'addServer'})
		}
	}
</script>

<style lang="scss">
    #test_reachability {
        width: auto;
        margin-right: 5px;
    }
    .adapter-config {
        .x-table-actionable {
            height: auto;
            .x-title {
                font-weight: 300;
            }
            thead th {
                font-weight: 200;
            }
        }
        .config-settings {
            margin-top: 64px;
            > .header {
                font-weight: 300;
                text-align: left;
                margin-bottom: 8px;
                .svg-icon {
                    margin-right: 8px;
                }
            }
            > .content {
                overflow: hidden;
                .x-tabs {
                    overflow: hidden;
                    width: 60vw;
                    &.shrinking-y {
                        transform: translateY(-100%);
                    }
                    .configuration {
                        width: calc(60vw - 72px);
                        padding: 24px;
                    }
                }
            }
        }
        .config-server {
            .x-logo-name {
                margin-bottom: 24px;
            }
            .server-error {
                display: flex;
                align-items: baseline;
                margin-bottom: 12px;
                .error-text {
                    margin-left: 8px;
                }
            }
        }
    }
</style>