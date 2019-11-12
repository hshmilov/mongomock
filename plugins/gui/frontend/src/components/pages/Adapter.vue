<template>
  <x-page
    :breadcrumbs="[
      { title: 'adapters', path: { name: 'Adapters'}},
      { title: title }
    ]"
    class="x-adapter"
  >
    <x-table-wrapper title="Add or Edit Connections" :loading="loading">
      <template slot="actions">
        <x-button
          v-if="selectedServers && selectedServers.length"
          link
          @click="removeConnection"
        >Remove</x-button>
        <x-button @click="configConnection('new')" id="new_connection" :disabled="isReadOnly">+ New Connection</x-button>
      </template>
      <x-table
        slot="table"
        :fields="tableFields"
        v-model="isReadOnly ? undefined : selectedServers"
        :on-click-row="isReadOnly ? undefined: configConnection"
        :data="adapterClients"
      />
    </x-table-wrapper>

    <div class="config-settings">
      <x-button link class="header" :disabled="isReadOnly" @click="toggleSettings">
        <svg-icon name="navigation/settings" :original="true" height="20" />Advanced Settings</x-button>
      <div class="content">
        <x-tabs v-if="currentAdapter && advancedSettings" class="growing-y" ref="tabs">
          <x-tab v-for="config, configName, i in currentAdapter.config"
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
          v-model="serverModal.serverData"
          :schema="adapterSchema"
          :api-upload="uploadFileEndpoint"
          @submit="saveServer"
          @validate="validateServer"
        />
        <div v-if="instances && instances.length > 0" id="serverInstancesList">
          <label for="serverInstance" align="left">Choose Instance</label>
          <x-select
            id="serverInstance"
            align="left"
            v-model="serverModal.instanceName"
            :options="instances"
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
        <x-button id="save_server" @click="saveServer" :disabled="!serverModal.valid">Save and Connect</x-button>
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
  import {parseVaultError} from '../../constants/utils'

    import {mapState, mapGetters, mapActions} from 'vuex'
    import {
        FETCH_ADAPTERS, 
        SAVE_ADAPTER_CLIENT, 
        ARCHIVE_CLIENT, 
        TEST_ADAPTER_SERVER, 
        HINT_ADAPTER_UP
    } from '../../store/modules/adapters'
    import {SAVE_PLUGIN_CONFIG} from '../../store/modules/settings'
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
        },
        isCyberarkVault(state) {
          return _get(state, 'configuration.data.global.cyberark_vault', false)
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
        const currentSchema = _get(this.currentAdapter, 'schema', null)
        if (currentSchema) currentSchema['useVault'] =  this.isCyberarkVault
        return currentSchema
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
          valid: false,
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
      configConnection(clientId) {
        this.message = ''
        this.serverModal.valid = true
        if (clientId === 'new') {
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
          if (client.error && client.error !== "" && client.error.startsWith("cyberark_vault_error")) {
            let result = parseVaultError(client.error);
            this.serverModal.serverData[result[1]].error = result[2]
            this.serverModal.error = result[2]
          }
        }
        this.toggleServerModal()
      },
      removeConnection() {
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

  #VaultQueryInput {
    width: 60%
  }

  .x-adapter {
    .x-table-wrapper {
      height: auto;
      .x-button#new_connection{
        width: 140px;
      }
      .table-title {
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
        display: flex;
        margin-bottom: 24px;
        .text {
          flex-grow: 1;
        }
        i {
          text-decoration: none;
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

      &.x-modal {
        .x-button {
          width: auto;
        }
      }

      .server-error {
        display: flex;
        align-items: baseline;
        margin-bottom: 12px;

        .error-text {
          margin-left: 8px;
          width: 100%;
          text-overflow: ellipsis;
          overflow: hidden;
        }
      }
    }

    .upload-file {
      .file-name {
        width: 120px;
      }
    }

    .x-vault-query-input {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 1001;
      display: grid;

      .modal-container {
        margin: auto;
        padding: 24px;
        background-color: $theme-white;
        border-radius: 2px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, .33);
        z-index: 1001;

        .modal-header {
          display: flex;
          border-bottom: 1px solid $grey-2;
          padding: 0 24px 12px;
          margin: 0 -24px 24px -24px;

          .title {
            flex: 1 0 auto;
            font-weight: 500;
            font-size: 16px;
          }
        }

        .modal-body {
          padding: 0;
          margin-bottom: 24px;

          .form-group:last-of-type {
            margin-bottom: 0;
          }
        }

        .modal-footer {
          border: 0;
          padding: 0;
          text-align: right;
        }
      }

      .modal-overlay {
        position: fixed;
        z-index: 1000;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, .5);
        transition: opacity .3s ease;
      }
    }

  }
</style>