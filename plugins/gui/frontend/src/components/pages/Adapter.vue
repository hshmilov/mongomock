<template>
  <x-page
    :breadcrumbs="[
    	{ title: 'adapters', path: { name: 'Adapters'}},
    	{ title: title }
    ]"
    class="x-adapter"
  >
    <x-table-wrapper title="Add or Edit Servers" :loading="loading">
      <template slot="actions">
        <x-button
          v-if="selectedServers && selectedServers.length"
          link
          @click="removeServers"
        >Remove</x-button>
        <x-button @click="configServer('new')" id="new_server" :disabled="isReadOnly">+ New Server</x-button>
      </template>
      <x-table
        slot="table"
        :fields="tableFields"
        v-model="isReadOnly ? undefined : selectedServers"
        :on-click-row="isReadOnly ? undefined: configServer"
        :data="adapterClients"
      />
    </x-table-wrapper>

    <div class="config-settings">
      <x-button link class="header" :disabled="isReadOnly" @click="toggleSettings">
        <svg-icon name="navigation/settings" :original="true" height="20" />Advanced Settings</x-button>
      <div class="content">
        <x-tabs v-if="currentAdapter && advancedSettings" class="growing-y" ref="tabs">
          <x-tab
            v-for="config, configName, i in currentAdapter.config"
            :key="i"
            :title="config.schema.pretty_name || configName"
            :id="configName"
            :selected="!i"
          >
            <div class="configuration">
              <x-form :schema="config.schema" v-model="config.config" @validate="validateConfig" />
              <x-button
                @click="saveConfig(configName, config.config)"
                tabindex="1"
                :disabled="!configValid"
              >Save Config</x-button>
            </div>
          </x-tab>
        </x-tabs>
      </div>
    </div>
    <x-modal
      v-if="serverModal.serverData && serverModal.uuid && serverModal.open"
      size="lg"
      class="config-server"
      @close="toggleServerModal"
      @confirm="saveServer"
      @enter="promptSaveServer"
    >
      <div slot="body">
        <!-- Container for configuration of a single selected / added server -->
        <x-title :logo="`adapters/${adapterId}`">
          {{ title }}
          <x-button
            v-if="adapterLink"
            slot="actions"
            header
            link
            class="help-link"
            title="More information about connecting this adapter"
            @click="openHelpLink"
          >
            <md-icon>help_outline</md-icon>Help
          </x-button>
        </x-title>
        <div class="server-error" v-if="serverModal.error">
          <svg-icon name="symbol/error" :original="true" height="12"></svg-icon>
          <div class="error-text">{{serverModal.error}}</div>
        </div>
        <x-form
          :schema="adapterSchema"
          v-model="serverModal.serverData"
          :api-upload="uploadFileEndpoint"
          @submit="saveServer"
          @validate="validateServer"
        />
        <div v-if="instances && instances.length > 0" id="serverInstancesList">
          <label for="serverInstance" align="left">Choose Instance</label>
          <x-select
            id="serverInstance"
            align="left"
            :options="instances"
            v-model="serverModal.instanceName"
          />
        </div>
      </div>
      <template slot="footer">
        <x-button link @click="toggleServerModal">Cancel</x-button>
        <x-button
          id="test_reachability"
          @click="testServer"
          :disabled="!serverModal.valid"
        >Test Reachability</x-button>
        <x-button id="save_server" @click="saveServer" :disabled="!serverModal.valid">Save</x-button>
      </template>
    </x-modal>
    <x-modal
      v-if="deleting"
      @close="closeConfirmDelete"
      @confirm="doRemoveServers"
      approve-text="Delete"
    >
      <div slot="body">
        Are you sure you want to delete this server?
        <br />
        <br />
        <input type="checkbox" id="deleteEntitiesCheckbox" v-model="deleteEntities" />
        <label for="deleteEntitiesCheckbox">Also delete all associated entities (devices, users)</label>
      </div>
    </x-modal>
    <x-toast v-if="message" v-model="message" :timeout="toastTimeout" />
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

    import {mapState, mapMutations, mapGetters, mapActions} from 'vuex'
    import {
        FETCH_ADAPTERS, 
        SAVE_ADAPTER_CLIENT, 
        ARCHIVE_CLIENT, 
        TEST_ADAPTER_SERVER, 
        HINT_ADAPTER_UP
    } from '../../store/modules/adapters'
    import {SAVE_PLUGIN_CONFIG} from '../../store/modules/settings'
    import {CHANGE_TOUR_STATE} from '../../store/modules/onboarding'
    import _get from 'lodash/get'
    import _isEmpty from 'lodash/isEmpty'

    export default {
        name: 'x-adapter',
        components: {
            xPage, xTableWrapper, xTable, xTabs, xTab, xForm, xModal, xSelect, xButton, xTitle, xToast
        },
        computed: {
            ...mapGetters(['getAdapterById', 'getClientsMap', 'getInstancesMap']),
            ...mapState({
                loading(state) {
                    return state.adapters.adapters.fetching
                },
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Adapters === 'ReadOnly'
                },
                allClients(state) {
                    return state.adapters.clients
                }
            }),
            adapterId() {
                return this.$route.params.id
            },
            currentAdapter() {
                return this.getAdapterById(this.adapterId) || {}
            },
            title() {
                return this.currentAdapter.title
            },
            adapterLink() {
                return this.currentAdapter.link
            },
            adapterClients() {
                const clients =  _get(this.currentAdapter, 'clients', [])
                const instances = this.getInstancesMap
                const res =  clients.map((c, index) => {
                    const client = this.getClientsMap.get(c)
                    const { node_id } = client
                    const instance = instances.get(node_id)

                    return {
                        ...client,
                        ...client.client_config,
                        node_name: instance.node_name
                    }
                })
                return res
            },
            instances() {
                const instancesIds =  _get(this.currentAdapter, 'instances', [])
                return instancesIds.map(instance => {
                    const i = this.getInstancesMap.get(instance)
                    return {
                        name: i.node_id,
                        title: i.node_name 
                    }
                })
            },
            adapterSchema() {
                return _get(this.currentAdapter, 'schema', null)
            },
            tableFields() {
                if (!this.adapterSchema || !this.adapterSchema.items) return []
                const fields =  [
                    {name: 'status', title: '', type: 'string', format: 'icon'},
                    {name: 'node_name', title: 'Instance Name', type: 'string'},
                    ...this.adapterSchema.items.filter(field => (field.type !== 'file' && field.format !== 'password'))
                ]
                return fields
                
            },
            uploadFileEndpoint() {
                return `adapters/${this.adapterId}/${this.serverModal.instanceName}`
            }
        },
        data() {
            return {
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
                changeState: CHANGE_TOUR_STATE
            }),
            ...mapActions({
                fetchAdapters: FETCH_ADAPTERS, 
                updateServer: SAVE_ADAPTER_CLIENT, 
                testAdapter: TEST_ADAPTER_SERVER,
                archiveServer: ARCHIVE_CLIENT, 
                updatePluginConfig: SAVE_PLUGIN_CONFIG, 
                hintAdapterUp: HINT_ADAPTER_UP
            }),
            openHelpLink() {
                window.open(this.adapterLink, '_blank')
            },
            configServer(clientId) {
                this.message = ''
                this.serverModal.valid = true
                if (clientId === 'new') {
                    // this.serverModal.instanceName = this.currentAdapter.title
                    this.serverModal = {
                        ...this.serverModal,
                        serverData: {},
                        serverName: 'New Server',
                        uuid: clientId,
                        error: '',
                        valid: false
                    }
                } else {
                    let client = this.adapterClients.find(c => c.uuid === clientId)
                    this.serverModal = {
                        ...this.serverModal,
                        serverData: {...client.client_config, oldInstanceName: client.node_id},
                        instanceName: client.node_id,
                        serverName: client.client_id,
                        uuid: client.uuid,
                        error: client.error,
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
            toggleSettings() {
                if (this.advancedSettings) {
                    this.$refs.tabs.$el.classList.add('shrinking-y')
                    setTimeout(() => this.advancedSettings = false, 1000)
                } else {
                    this.advancedSettings = true
                }
            },
            setDefaultInstance () {
                let instance = this.instances.find(i => i.title === 'Master') || this.instances[0]
                this.serverModal.instanceName = instance.name
            }
        },
        created() {
            this.hintAdapterUp(this.adapterId)
            if (_isEmpty(this.currentAdapter)) {
                this.fetchAdapters().then(this.setDefaultInstance)
            } else {
              this.setDefaultInstance()
            }
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