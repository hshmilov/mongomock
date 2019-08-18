<template>
    <x-page :breadcrumbs="[
    	{ title: 'adapters', path: { name: 'Adapters'}},
    	{ title: adapterName }
    ]" class="x-adapter">
        <x-table-wrapper title="Add or Edit Servers" :loading="loading">
            <template slot="actions">
                <x-button v-if="selectedServers && selectedServers.length" link @click="removeServers">Remove</x-button>
                <x-button @click="configServer('new')" id="new_server" :disabled="isReadOnly">+ New Server</x-button>
            </template>
            <x-table slot="table" :fields="tableFields" v-model="isReadOnly? undefined: selectedServers"
                     :on-click-row="isReadOnly? undefined: configServer" :data="adapterClients"/>
        </x-table-wrapper>

        <div class="config-settings">
            <x-button link class="header" :disabled="isReadOnly" @click="toggleSettings">
                <svg-icon name="navigation/settings" :original="true" height="20"/>Advanced Settings</x-button>
            <div class="content">
                <x-tabs v-if="currentAdapter && currentAdapter[0] && advancedSettings" class="growing-y" ref="tabs">
                    <x-tab v-for="config, configName, i in currentAdapter[0].config" :key="i"
                           :title="config.schema.pretty_name || configName" :id="configName" :selected="!i">
                        <div class="configuration">
                            <x-form :schema="config.schema" v-model="config.config" @validate="validateConfig"/>
                            <x-button @click="saveConfig(configName, config.config)" tabindex="1" :disabled="!configValid">Save Config</x-button>
                        </div>
                    </x-tab>
                </x-tabs>
            </div>
        </div>
        <x-modal v-if="serverModal.serverData && serverModal.uuid && serverModal.open" size="lg" class="config-server"
                 @close="toggleServerModal" @confirm="saveServer" @enter="promptSaveServer">
            <div slot="body">
                <!-- Container for configuration of a single selected / added server -->
                <x-title :logo="`adapters/${adapterPluginName}`">
                    {{ adapterName }}
                    <x-button v-if="adapterLink" slot="actions"
                              header
                              link
                              class="help-link"
                              title="More information about connecting this adapter"
                              @click="openHelpLink">
                        <md-icon>help_outline</md-icon>Help</x-button>
                </x-title>
                <div class="server-error" v-if="serverModal.error">
                    <svg-icon name="symbol/error" :original="true" height="12"></svg-icon>
                    <div class="error-text">{{serverModal.error}}</div>
                </div>
                <x-form :schema="adapterSchema" v-model="serverModal.serverData"
                        :api-upload="`adapters/${adapterId}/${serverModal.instanceName}`"
                        @submit="saveServer" @validate="validateServer"/>
                <div v-if="instances && instances.length > 0" id="serverInstancesList">
                    <label for="serverInstance" align="left">Choose Instance</label>
                    <x-select id="serverInstance" align="left" :options="instances" v-model="serverModal.instanceName"/>
                </div>
            </div>
            <template slot="footer">
                <x-button link @click="toggleServerModal">Cancel</x-button>
                <x-button id="test_reachability" @click="testServer" :disabled="!serverModal.valid">Test Reachability</x-button>
                <x-button id="save_server" @click="saveServer" :disabled="!serverModal.valid">Save</x-button>
            </template>
        </x-modal>
        <x-modal v-if="deleting" @close="closeConfirmDelete" @confirm="doRemoveServers" approve-text="Delete">
            <div slot="body">Are you sure you want to delete this server? <br/><br/>
                <input type="checkbox" id="deleteEntitiesCheckbox" v-model="deleteEntities">
                <label for="deleteEntitiesCheckbox">Also delete all associated entities (devices, users)</label>
            </div>
        </x-modal>
        <x-toast v-if="message" v-model="message" :timeout="toastTimeout"/>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTableWrapper from '../axons/tables/TableWrapper.vue'
    import xTable from '../axons/tables/Table.vue'
    import xTabs from '../axons/tabs/Tabs.vue'
    import xTab from '../axons/tabs/Tab.vue'
    import xForm from '../neurons/schema/Form.vue'
    import xModal from '../axons/popover/Modal.vue'
    import xSelect from '../axons/inputs/Select.vue'
    import xButton from '../axons/inputs/Button.vue'
    import xTitle from '../axons/layout/Title.vue'
    import xToast from '../axons/popover/Toast.vue'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {
        FETCH_ADAPTERS, UPDATE_CURRENT_ADAPTER, SAVE_ADAPTER_SERVER, ARCHIVE_SERVER, TEST_ADAPTER_SERVER
    } from '../../store/modules/adapters'
    import {pluginMeta} from '../../constants/plugin_meta.js'
    import {SAVE_PLUGIN_CONFIG} from '../../store/modules/settings'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'

    export default {
        name: 'x-adapter',
        components: {
            xPage, xTableWrapper, xTable, xTabs, xTab, xForm, xModal, xSelect, xButton, xTitle, xToast
        },
        computed: {
            ...mapState({
                currentAdapter(state) {
                    return state.adapters.currentAdapter
                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Adapters === 'ReadOnly'
                }
            }),
            adapterId() {
                return this.$route.params.id
            },
            adapterPluginName() {
                return this.adapterId
            },
            adapterName() {
                if (!pluginMeta[this.adapterPluginName]) {
                    return this.adapterPluginName
                }
                return pluginMeta[this.adapterPluginName].title
            },
            adapterLink() {
                if (!pluginMeta[this.adapterPluginName]) {
                    return null
                }
                return pluginMeta[this.adapterPluginName].link
            },
            adapterClients() {
                if (!this.currentAdapter) return []
                let clients = []
                Object.values(this.currentAdapter).filter(field => (field.clients && field.clients.length > 0)).forEach(currentAdapter =>
                    currentAdapter.clients.forEach(currentClient =>
                        clients.push({
                            uuid: currentClient.uuid,
                            status: currentClient.status,
                            node_id: currentClient.node_id,
                            node_name: currentAdapter.node_name,
                            ...currentClient.client_config,
                            error: currentClient.error
                        })
                    )
                )
                return clients
            },
            instances() {
                if (!this.currentAdapter) return []
                let instancesList = Object.values(this.currentAdapter).filter(field => (field.node_id)).map((adapter) => {
                    if (adapter.node_name && adapter.node_name !== '') {
                        return {name: adapter.node_id, title: adapter.node_name}
                    } else if (adapter.node_id) {
                        return {name: adapter.node_id, title: adapter.node_id}
                    }
                })
                return instancesList
            },
            adapterSchema() {
                if (!this.currentAdapter) return null
                return this.currentAdapter[0].schema
            },
            tableFields() {
                if (!this.adapterSchema || !this.adapterSchema.items) return []
                return [
                    {name: 'status', title: '', type: 'string', format: 'icon'},
                    {name: 'node_name', title: 'Instance Name', type: 'string'},
                    ...this.adapterSchema.items.filter(field => (field.type !== 'file' && field.format !== 'password'))
                ]
            }
        },
        data() {
            return {
                loading: false,
                serverModal: {
                    open: false,
                    serverData: {},
                    instanceName: '',
                    error: '',
                    serverName: 'New Server',
                    uuid: null,
                    valid: false
                },
                selectedServers: [],
                message: '',
                toastTimeout: 60000,
                advancedSettings: false,
                configValid: true,
                deleting: false,        // whether or not the modal for deleting confirmation is displayed
                deleteEntities: false  // if 'deleting = true' and deleting was confirmed this means that
                // also the entities of the associated users should be deleted
            }
        },
        methods: {
            ...mapMutations({
                updateAdapter: UPDATE_CURRENT_ADAPTER, changeState: CHANGE_TOUR_STATE
            }),
            ...mapActions({
                fetchAdapters: FETCH_ADAPTERS, updateServer: SAVE_ADAPTER_SERVER, testAdapter: TEST_ADAPTER_SERVER,
                archiveServer: ARCHIVE_SERVER, updatePluginConfig: SAVE_PLUGIN_CONFIG
            }),
            openHelpLink() {
                window.open(this.adapterLink, '_blank')
            },
            configServer(serverId) {
                this.message = ''
                this.serverModal.valid = true
                if (serverId === 'new') {
                    this.serverModal.instanceName = this.instances[0].name
                    this.serverModal = {
                        ...this.serverModal,
                        serverData: {instanceName: null},
                        serverName: 'New Server',
                        uuid: serverId,
                        error: '',
                        valid: false
                    }
                } else {
                    let server = null
                    Object.values(this.currentAdapter).filter(field => (field.clients && field.clients.length > 0)).forEach((unique_adapter) => {
                        if (unique_adapter.clients.find(client => (client.uuid === serverId))) {
                            server = unique_adapter.clients.find(client => (client.uuid === serverId))
                        }
                    })
                    this.serverModal = {
                        ...this.serverModal,
                        serverData: {...server.client_config, oldInstanceName: server.node_id},
                        instanceName: server.node_id,
                        serverName: server.client_id,
                        uuid: server.uuid,
                        error: server.error,
                        valid: true
                    }
                }
                this.toggleServerModal()
            },
            promptSaveServer() {
                this.changeState({name: 'saveServer'})
            },
            removeServers() {
                if (this.isReadOnly) return
                this.deleting = true
            },
            doRemoveServers() {
                this.selectedServers.forEach(serverId => this.archiveServer({
                    nodeId: this.adapterClients.find(client => (client.uuid === serverId)).node_id,
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
            saveServer() {
                this.message = 'Connecting to Server...'
                this.updateServer({
                    adapterId: this.adapterId,
                    serverData: {...this.serverModal.serverData, instanceName: this.serverModal.instanceName},
                    uuid: this.serverModal.uuid
                }).then((updateRes) => {
                    if (this.selectedServers.includes('')) {
                        this.selectedServers.push(updateRes.data.id)
                        this.selectedServers = this.selectedServers.filter(selected => selected !== '')
                    }
                    if (updateRes.data.status === 'error') {
                        this.message = 'Problem connecting. Review error and try again.'
                    } else {
                        this.message = 'Connection established. Data collection initiated...'
                    }
                  ((data) => {
                    this.$nextTick(() => {
                      this.changeState({
                        name: `${data.status}Server`,
                        id: data.id
                      })
                    })
                  })(updateRes.data)
                }).catch((error)=>{
                    this.message = error.response.data.message
                })
                this.toggleServerModal()
            },
            testServer() {
                this.message = 'Testing server connection...'
                this.testAdapter({
                    adapterId: this.adapterId,
                    serverData: {...this.serverModal.serverData, instanceName: this.serverModal.instanceName},
                    uuid: this.serverModal.uuid
                }).then((updateRes) => {
                    if (updateRes.data.status === 'error') {
                        if (updateRes.data.type === 'NotImplementedError') {
                            this.message = 'Test reachability is not supported for this adapter.'
                        } else {
                            this.message = 'Problem connecting to server.'
                        }
                    } else {
                        this.message = 'Connection is valid.'
                    }
                    setTimeout(() => {
                        this.message = ''
                    }, 60000)
                }).catch((error) => {
                    if (error.response.data.type === 'NotImplementedError') {
                        this.message = 'Test reachability is not supported for this adapter.'
                    } else {
                        this.message = 'Problem connecting to server.'
                    }
                    setTimeout(() => {
                        this.message = ''
                    }, 60000)
                })
            },
            toggleServerModal() {
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
        created() {
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

    #serverInstancesList {
        width: 45%
    }

    .x-adapter {
        .x-table-wrapper {
            height: auto;

            .title {
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
            .x-title {
                i {
                    text-decoration: none;
                }
            }
        }

        .config-server {
            .x-title {
                display: flex;
                margin-bottom: 24px;
                .text {
                    flex-grow: 1;
                }

                &:hover {
                    box-shadow: none;
                    i {
                        color: $theme-orange;
                    }
                }

                .help-link {
                    padding-right: 0;
                    i {
                        font-size: 20px!important;
                    }
                }
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

        .upload-file {
            .file-name {
                width: 120px;
            }
        }
    }
</style>