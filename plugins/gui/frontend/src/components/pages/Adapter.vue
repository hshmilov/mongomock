<template>
  <XPage
    :breadcrumbs="[
      { title: 'adapters', path: { name: 'Adapters'}},
      { title: title }
    ]"
    class="x-adapter"
  >
    <XRoleGateway
      :permission-category="$permissionConsts.categories.Adapters"
      :permission-section="$permissionConsts.categories.Connections"
    >
      <template slot-scope="{ canAdd, canUpdate, canDelete }">
        <XTableWrapper
          title="Add or Edit Connections"
          :loading="loading"
        >
          <template slot="actions">
            <XButton
              v-if="canDelete && selectedServers && selectedServers.length"
              type="link"
              @click="removeConnection"
            >Delete</XButton>
            <XButton
              id="new_connection"
              type="primary"
              :disabled="!canAdd"
              @click="configConnection('new')"
            >Add Connection</XButton>
          </template>
          <XTable
            slot="table"
            v-model="selectedServersModel"
            type="primary"
            :fields="tableFields"
            :on-click-row="canUpdate ? configConnection : undefined"
            :data="adapterClients"
            :multiple-row-selection="canDelete"
          />
        </XTableWrapper>
        <XAdapterTunnelConnectionMessage
          v-if="showTunnelConnectionMessage"
          :status="tunnelStatus"
          :use-tunnel-setting="useTunnelSetting"
          @open-settings="openSettings"
        />
        <div class="config-settings">
          <XButton
            type="link"
            class="header"
            :disabled="cannotOpenAdvancedSettings"
            @click="toggleSettings"
          >
            <AIcon
              type="setting"
              theme="filled"
              class="setting_cog"
            />
            Advanced Settings
          </XButton>
          <div class="content">
            <XAdapterAdvancedSettings
              v-if="currentAdapter && advancedSettings"
              :adapter-unique-name="pluginUniqueName"
              @save="saveConfig"
            />
          </div>
        </div>
        <XModal
          v-if="(canUpdate || canAdd)
            && serverModal.serverData && serverModal.uuid && serverModal.open"
          size="lg"
          class="config-server"
          :class="{'fixed-size': connectionDiscoveryEnabled}"
          @close="toggleServerModal"
          @confirm="saveServer"
        >
          <div slot="body">
            <!-- Container for configuration of a single selected / added server -->
            <XTitle :logo="`adapters/${adapterId}`">
              {{ title }}
              <XButton
                v-if="adapterLink"
                slot="actions"
                header
                type="link"
                class="help-link"
                title="More information about connecting this adapter"
                @click="openHelpLink"
              >
                <XIcon type="question-circle" />Help
              </XButton>
            </XTitle>
            <template v-if="connectionDiscoveryEnabled">
              <ATabs
                default-active-key="1"
                :centered="true"
                :animated="false"
              >
                <TabPane
                  key="1"
                  tab="Connection Configuration"
                >
                  <XAdapterClientConnection
                    v-model="serverModal"
                    :adapter-schema="adapterSchema"
                    :error="connectionLabelError"
                    :require-connection-label="requireConnectionLabel"
                    :adapter-id="adapterId"
                    @errorUpdate="updateErrorLabel"
                    @validate="validateServer"
                  />
                </TabPane>
                <TabPane
                  key="2"
                  tab="Scheduling Configuration"
                >
                  <div class="discovery-configuration">
                    <XForm
                      v-model="serverModal.serverData.connection_discovery"
                      :schema="connectionDiscoverySchema"
                      :error="connectionLabelError"
                      wrapping-class="discovery-configuration"
                      @validate="validateConnectionDiscovery"
                    />
                  </div>
                </TabPane>
              </ATabs>
            </template>
            <XAdapterClientConnection
              v-else
              v-model="serverModal"
              :adapter-schema="adapterSchema"
              :error="connectionLabelError"
              :require-connection-label="requireConnectionLabel"
              :adapter-id="adapterId"
              @errorUpdate="updateErrorLabel"
              @validate="validateServer"
            />
          </div>
          <template slot="footer">
            <XButton
              type="link"
              @click="toggleServerModal"
            >Cancel</XButton>
            <XButton
              id="test_reachability"
              type="primary"
              :disabled="!serverModal.valid || !serverModal.connectionValid || !connectionLabelValid"
              @click="testServer"
            >Test Reachability</XButton>
            <XButton
              id="save_server"
              type="primary"
              :disabled="!serverModal.valid || !serverModal.connectionValid || !connectionLabelValid"
              @click="saveServer"
            >Save and Connect</XButton>
          </template>
        </XModal>
        <XModal
          v-if="deleting"
          approve-text="Delete"
          @close="closeConfirmDelete"
          @confirm="doRemoveServers"
        >
          <div slot="body">
            Are you sure you want to delete this server?
            <br>
            <br>
            <input
              id="deleteEntitiesCheckbox"
              v-model="deleteEntities"
              type="checkbox"
            >
            <label
              for="deleteEntitiesCheckbox"
            >Also delete all associated entities (devices, users)</label>
          </div>
        </XModal>
        <XToast
          v-if="message"
          v-model="message"
          :timeout="toastTimeout"
        />
      </template>
    </XRoleGateway>
  </XPage>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import _get from 'lodash/get';
import _set from 'lodash/set';
import XIcon from '@axons/icons/Icon';
import XPage from '@axons/layout/Page.vue';
import XTableWrapper from '@axons/tables/TableWrapper.vue';
import XTable from '@axons/tables/Table.vue';
import XModal from '@axons/popover/Modal/index.vue';
import XButton from '@axons/inputs/Button.vue';
import XTitle from '@axons/layout/Title.vue';
import XToast from '@axons/popover/Toast.vue';
import XAdapterTunnelConnectionMessage from '@neurons/alerts/AdapterTunnelConnectionMessage.vue';
import { parseVaultError } from '@constants/utils';
import { FETCH_SYSTEM_CONFIG } from '@store/actions';
import {
  FETCH_ADAPTER_CONNECTIONS,
  ARCHIVE_CLIENT,
  LAZY_FETCH_ADAPTERS,
  HINT_ADAPTER_UP,
  SAVE_ADAPTER_CLIENT,
  TEST_ADAPTER_SERVER,
  LAZY_FETCH_ADAPTERS_CLIENT_LABELS,
  LOAD_ADAPTER_CONFIG,
} from '@store/modules/adapters';
import XForm from '@neurons/schema/Form.vue';
import XAdapterAdvancedSettings from '@networks/adapters/adapter-advanced-settings.vue';
import { Icon, Tabs as ATabs } from 'ant-design-vue';

import { tunnelConnectionStatuses } from '@constants/settings';
import { GET_CONNECTION_LABEL, REQUIRE_CONNECTION_LABEL } from '../../store/getters';
import { SAVE_PLUGIN_CONFIG } from '../../store/modules/settings';
import XAdapterClientConnection from '@networks/adapters/adapter-client-connection.vue';

export default {
  name: 'XAdapter',
  components: {
    XPage,
    XTableWrapper,
    XTable,
    XForm,
    XModal,
    XButton,
    XTitle,
    XToast,
    AIcon: Icon,
    XIcon,
    XAdapterAdvancedSettings,
    XAdapterTunnelConnectionMessage,
    ATabs,
    TabPane: ATabs.TabPane,
    XAdapterClientConnection,
  },
  data() {
    return {
      serverModal: {
        open: false,
        serverData: {},
        instanceId: '',
        connectionLabel: '',
        error: '',
        serverName: 'New Server',
        uuid: null,
        valid: false,
      },
      loading: true,
      connectionLabelError: '',
      showConnectionLabelBorder: false,
      selectedServers: [],
      message: '',
      toastTimeout: 60000,
      advancedSettings: false,
      useTunnelSetting: undefined,
      deleting: false, // whether or not the modal for deleting confirmation is displayed
      deleteEntities: false, // if 'deleting = true' and deleting was confirmed this means that
      // also the entities of the associated users should be deleted
      connectionDiscoverySchema: null,
    };
  },
  computed: {
    ...mapGetters({
      getAdapterById: 'getAdapterById',
      getInstancesMap: 'getInstancesMap',
      requireConnectionLabel: REQUIRE_CONNECTION_LABEL,
      getConnectionLabel: GET_CONNECTION_LABEL,
    }),
    ...mapState({
      connections(state) {
        return _get(state, `adapters.clients.${this.adapterId}`, []);
      },
      isPasswordVaultEnabled(state) {
        return _get(state, 'configuration.data.global.passwordManagerEnabled', false);
      },
      adapterSchema(state) {
        const schema = _get(state, `adapters.adapterSchemas.${this.adapterId}`);
        return schema;
      },
      tunnelStatus(state) {
        return _get(state, 'dashboard.lifecycle.data.tunnelStatus', tunnelConnectionStatuses.notAvailable);
      },
      connectionDiscoveryEnabled(state) {
        return _get(state.settings,
          `configurable.${this.adapterId}.DiscoverySchema.config.connection_discovery.enabled`,
          false) || this.adapterConnectionDiscoveryEnabled;
      },
      defaultConnectionDiscovery(state) {
        return _get(state.settings,
          `configurable.${this.adapterId}.DiscoverySchema.config.adapter_discovery`,
          {});
      },
    }),
    connectionLabelValid() {
      return !this.requireConnectionLabel || this.serverModal.connectionLabel;
    },
    showTunnelConnectionMessage() {
      return this.tunnelStatus.toString() !== tunnelConnectionStatuses.notAvailable;
    },
    cannotOpenAdvancedSettings() {
      return this.$cannot(this.$permissionConsts.categories.Adapters,
        this.$permissionConsts.actions.Update);
    },
    selectedServersModel: {
      get() {
        return this.selectedServers;
      },
      set(value) {
        this.selectedServers = value;
      },
    },
    adapterId() {
      return this.$route.params.id;
    },
    currentAdapter() {
      return this.getAdapterById(this.adapterId) || {};
    },
    pluginUniqueName() {
      return this.currentAdapter.pluginUniqueName;
    },
    title() {
      return this.currentAdapter.title;
    },
    adapterLink() {
      return this.currentAdapter.link;
    },
    adapterClients() {
      const instances = this.getInstancesMap;
      return this.connections.map((client) => {
        // eslint-disable-next-line camelcase
        const { node_id } = client;
        const instance = instances.get(node_id);

        return {
          ...client,
          ...client.client_config,
          node_name: instance.node_name,
          connection_label: client.connectionLabel || this.getConnectionLabel(client.client_id, {
            plugin_name: this.adapterId, node_id,
          }),
        };
      });
    },
    instances() {
      const instancesIds = _get(this.currentAdapter, 'instances', []);
      return instancesIds.map((instance) => {
        const i = this.getInstancesMap.get(instance);
        return {
          name: i.node_id,
          title: i.node_name,
        };
      });
    },
    instanceDefaultName() {
      if (!this.instances.length) return '';
      const instance = this.instances.find((i) => i.title === 'Master') || this.instances[0];
      return instance.name;
    },
    tableFields() {
      if (!this.adapterSchema || !this.adapterSchema.items) return [];
      return [
        {
          name: 'status',
          title: '',
          type: 'string',
          format: 'icon',
        },
        {
          name: 'node_name',
          title: 'Instance Name',
          type: 'string',
        },
        {
          name: 'connection_label',
          title: 'Connection Label',
          type: 'string',
        },
        ...this.adapterSchema.items.filter((field) => (field.type !== 'file' && field.format !== 'password')),
      ];
    },
    isSpecificConnectionDiscoverySet() {
      return _get(this.serverModal, 'serverData.connection_discovery.enabled', null);
    },
  },
  watch: {
    instanceDefaultName() {
      /**
       * Set the watch to be invoked after adapters have been loaded.
       * That has been set for when the user navigates directly to the adapter page.
       */
      this.setDefaultInstance();
    },
    isSpecificConnectionDiscoverySet(value, oldValue) {
      if (value && oldValue === false) {
        /**
         *  Settings the current adapter default settings when
         *  enabling connection discovery for the first time.
         */
        _set(this.serverModal, 'serverData.connection_discovery', {
          ...this.defaultConnectionDiscovery,
          enabled: true,
        });
      }
    },
  },
  async created() {
    this.fetchConfig();
    this.hintAdapterUp(this.adapterId);
    await this.lazyFetchAdapters();
    const { settings, connectionDiscoverySchema } = await this.fetchAdapterConnections(this.adapterId);
    this.useTunnelSetting = settings.connect_via_tunnel;
    this.connectionDiscoverySchema = connectionDiscoverySchema;
    await this.loadAdapterConfig({
      pluginId: this.adapterId,
      configName: 'DiscoverySchema',
    });
    this.loading = false;
    await this.lazyFetchConnectionLabels();
    this.setDefaultInstance();
  },
  methods: {
    ...mapActions({
      fetchAdapterConnections: FETCH_ADAPTER_CONNECTIONS,
      lazyFetchAdapters: LAZY_FETCH_ADAPTERS,
      updateServer: SAVE_ADAPTER_CLIENT,
      testAdapter: TEST_ADAPTER_SERVER,
      archiveServer: ARCHIVE_CLIENT,
      updatePluginConfig: SAVE_PLUGIN_CONFIG,
      hintAdapterUp: HINT_ADAPTER_UP,
      fetchConfig: FETCH_SYSTEM_CONFIG,
      lazyFetchConnectionLabels: LAZY_FETCH_ADAPTERS_CLIENT_LABELS,
      loadAdapterConfig: LOAD_ADAPTER_CONFIG,
    }),
    openHelpLink() {
      window.open(this.adapterLink, '_blank');
    },
    configConnection(clientId) {
      this.message = '';
      this.serverModal.valid = true;
      this.serverModal.connectionValid = true;
      if (clientId === 'new') {
        this.serverModal = {
          ...this.serverModal,
          serverData: {
            client_config: {},
            connection_discovery: { enabled: false },
          },
          serverName: 'New Server',
          uuid: clientId,
          error: '',
          valid: false,
        };
      } else {
        const client = this.adapterClients.find((c) => c.uuid === clientId);
        this.serverModal = {
          ...this.serverModal,
          serverData: {
            client_config: {
              ...client.client_config,
            },
            connection_discovery: {
              ...this.defaultConnectionDiscovery,
              ...client.connection_discovery,
            },
          },
          instanceIdPrev: client.node_id,
          instanceId: client.node_id,
          serverName: client.client_id,
          connectionLabel: client.connection_label,
          uuid: client.uuid,
          error: client.error,
          valid: true,
        };
        if (client.error && client.error !== '' && client.error.includes('_vault_error')) {
          const { field, error } = parseVaultError(client.error);
          this.serverModal.serverData.client_config[field].error = error;
          this.serverModal.error = error;
        }
      }
      this.toggleServerModal();
    },
    removeConnection() {
      this.deleting = true;
    },
    async doRemoveServers() {
      // eslint-disable-next-line no-restricted-syntax
      for (const serverId of this.selectedServers) {
        // eslint-disable-next-line no-await-in-loop
        await this.archiveServer({
          nodeId: this.adapterClients.find((client) => (client.uuid === serverId)).node_id,
          adapterId: this.adapterId,
          serverId,
          deleteEntities: this.deleteEntities,
        });
      }
      this.selectedServers = [];
      this.deleting = false;
    },
    closeConfirmDelete() {
      this.deleting = false;
      this.deleteEntities = false;
    },
    validateServer(valid) {
      this.serverModal.valid = valid;
      if (!valid) {
        this.connectionLabelError = '';
      }
    },
    validateConnectionDiscovery(valid) {
      this.serverModal.connectionValid = valid;
    },
    updateErrorLabel(value) {
      this.connectionLabelError = value;
    },
    saveServer() {
      this.message = 'Connecting to Server...';
      this.updateServer({
        adapterId: this.adapterId,
        clientId: this.serverModal.serverName,
        serverData: this.serverModal.serverData,
        connectionLabel: this.serverModal.connectionLabel,
        instanceId: this.serverModal.instanceId,
        instanceIdPrev: this.serverModal.instanceIdPrev,
        uuid: this.serverModal.uuid,
      }).then((updateRes) => {
        if (this.selectedServers.includes('')) {
          this.selectedServers.push(updateRes.data.id);
          this.selectedServers = this.selectedServers.filter((selected) => selected !== '');
        }
        if (updateRes.data.status === 'error') {
          this.message = 'Problem connecting. Review error and try again.';
        } else {
          this.message = 'Connection established. Data collection initiated...';
        }
      }).catch((error) => {
        this.message = error.response.data.message;
      });
      this.toggleServerModal();
    },
    testServer() {
      this.message = 'Testing server connection...';
      this.testAdapter({
        adapterId: this.adapterId,
        serverData: this.serverModal.serverData,
        instanceId: this.serverModal.instanceId,
        uuid: this.serverModal.uuid,
      }).then((updateRes) => {
        if (updateRes.data.status === 'error') {
          if (updateRes.data.type === 'NotImplementedError') {
            this.message = 'Test reachability is not supported for this adapter.';
          } else {
            this.message = 'Problem connecting to server.';
          }
        } else {
          this.message = 'Connection is valid.';
        }
        setTimeout(() => {
          this.message = '';
        }, 60000);
      }).catch((error) => {
        if (error.response.data.type === 'NotImplementedError') {
          this.message = 'Test reachability is not supported for this adapter.';
        } else {
          this.message = 'Problem connecting to server.';
        }
        setTimeout(() => {
          this.message = '';
        }, 60000);
      });
    },
    toggleServerModal() {
      this.serverModal.open = !this.serverModal.open;
      if (!this.serverModal.open) this.serverModal.connectionLabel = '';
    },

    saveConfig({ configName, config }) {
      this.message = 'Adapter configuration saving in progress...';
      this.updatePluginConfig({
        prefix: 'adapters',
        pluginId: this.adapterId,
        configName,
        config,
      }).then(() => {
        this.message = 'Adapter configuration saved';
        setTimeout(() => {
          this.message = '';
        }, 5000);
        this.useTunnelSetting = config.connect_via_tunnel;
        return true;
      });
    },
    toggleSettings() {
      this.advancedSettings = !this.advancedSettings;
    },
    openSettings() {
      this.advancedSettings = true;
    },
    setDefaultInstance() {
      this.serverModal.instanceId = this.instanceDefaultName;
    },
  },
};
</script>

<style lang="scss">
  #test_reachability {
    width: auto;
    margin-right: 5px;
  }

  #VaultQueryInput {
    width: 60%
  }

  .double-column {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-gap: 12px 24px;
    input {
      width: 100%;
      height: 32px;
    }
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
    .tunnel-connection-message {
      margin-top: 20px;
      padding-left: 16px;
      + .config-settings {
        margin-top: 20px;
      }
    }
    .config-settings {
      margin-top: 64px;

      > .header {
        font-weight: 300;
        text-align: left;
        margin-bottom: 8px;
        .setting_cog {
          font-size: 20px;
        }
        &:hover .setting_cog {
          color: $theme-orange;
        }
        span {
              vertical-align: top;
        }
        .svg-icon {
          margin-right: 8px;
        }
      }
      > .content {
        overflow: hidden;
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
        justify-content: center;
        margin-bottom: 12px;
        align-items: center;

        .error-text {
          margin-left: 8px;
          width: 100%;
          text-overflow: ellipsis;
          overflow: hidden;
        }
        .x-icon {
          font-size: 14px;
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

    #connectionLabel.error-border {
      border: 1px solid $indicator-error;
    }

    .discovery-configuration {
      padding-left: 5px;

      > .x-form > .x-array-edit .list {
        grid-template-columns: 1fr;

        .item_repeat_every input {
          width: 200px;
        }

        .item_system_research_rate input {
          width: 200px;
        }

        .ant-form-item .repeat_on_select {
          width: 400px;
        }
      }
    }

    .configuration .item_system_research_rate input {
      width: 200px;
    }

    .fixed-size {
      .modal-body {
        height: 500px;
      }
    }

  }
</style>
