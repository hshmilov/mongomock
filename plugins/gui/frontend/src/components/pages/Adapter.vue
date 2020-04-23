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
            >Remove</XButton>
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
            :fields="tableFields"
            :on-click-row="canUpdate ? configConnection : undefined"
            :data="adapterClients"
            :multiple-row-selection="canDelete"
          />
        </XTableWrapper>
        <div class="config-settings">
          <XButton
            type="link"
            class="header"
            :disabled="cannotOpenAdvancesSettings"
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
            <XTabs
              v-if="currentAdapter && advancedSettings"
              ref="tabs"
              class="growing-y"
            >
              <XTab
                v-for="(config, configName, i) in currentAdapter.config"
                :id="configName"
                :key="i"
                :title="config.schema.pretty_name || configName"
                :selected="!i"
              >
                <div class="configuration">
                  <XForm
                    v-model="config.config"
                    :schema="config.schema"
                    @validate="validateConfig"
                  />
                  <XButton
                    type="primary"
                    tabindex="1"
                    :disabled="!configValid"
                    @click="saveConfig(configName, config.config)"
                  >Save Config</XButton>
                </div>
              </XTab>
            </XTabs>
          </div>
        </div>
        <XModal
          v-if="(canUpdate || canAdd)
            && serverModal.serverData && serverModal.uuid && serverModal.open"
          size="lg"
          class="config-server"
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
                <MdIcon>help_outline</MdIcon>Help
              </XButton>
            </XTitle>
            <div
              v-if="serverModal.error"
              class="server-error"
            >
              <SvgIcon
                name="symbol/error"
                :original="true"
                height="12"
              />
              <div class="error-text">
                {{ serverModal.error }}
              </div>
            </div>
            <XForm
              v-model="serverModal.serverData"
              :schema="adapterSchema"
              :api-upload="uploadFileEndpoint"
              :error="connectionLabelError"
              @submit="saveServer"
              @validate="validateServer"
            />
            <div class="double-column">
              <div>
                <label for="connectionLabel">
                  Connection Label
                  <div
                    v-if="!requireConnectionLabel"
                    class="hint"
                  >optional</div>
                </label>
                <input
                  id="connectionLabel"
                  v-model="serverModal.connectionLabel"
                  :class="{ 'error-border': showConnectionLabelBorder }"
                  :maxlength="20"
                  @input="onConnectionLabelInput"
                  @blur="onConnectionLabelBlur"
                >
              </div>
              <XInstancesSelect
                id="serverInstance"
                v-model="serverModal.instanceName"
                :render-label="true"
                render-label-text="Choose Instance"
                :hide-in-one-option="true"
              />
            </div>
          </div>
          <template slot="footer">
            <XButton
              type="link"
              @click="toggleServerModal"
            >Cancel</XButton>
            <XButton
              id="test_reachability"
              type="primary"
              :disabled="!serverModal.valid || !connectionLabelValid"
              @click="testServer"
            >Test Reachability</XButton>
            <XButton
              id="save_server"
              type="link"
              :disabled="!serverModal.valid || !connectionLabelValid"
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
import _isEmpty from 'lodash/isEmpty';
import XPage from '@axons/layout/Page.vue';
import XTableWrapper from '@axons/tables/TableWrapper.vue';
import XTable from '@axons/tables/Table.vue';
import XTabs from '@axons/tabs/Tabs.vue';
import XTab from '@axons/tabs/Tab.vue';
import XModal from '@axons/popover/Modal/index.vue';
import XButton from '@axons/inputs/Button.vue';
import XTitle from '@axons/layout/Title.vue';
import XToast from '@axons/popover/Toast.vue';
import { parseVaultError } from '@constants/utils';
import { FETCH_SYSTEM_CONFIG } from '@store/actions';
import XForm from '@neurons/schema/Form.vue';
import { Icon } from 'ant-design-vue';

import {
  ARCHIVE_CLIENT,
  LAZY_FETCH_ADAPTERS,
  HINT_ADAPTER_UP,
  SAVE_ADAPTER_CLIENT,
  TEST_ADAPTER_SERVER,
} from '../../store/modules/adapters';
import { REQUIRE_CONNECTION_LABEL } from '../../store/getters';
import { SAVE_PLUGIN_CONFIG } from '../../store/modules/settings';
import { XInstancesSelect } from '../axons/inputs/dynamicSelects';

export default {
  name: 'XAdapter',
  components: {
    XPage,
    XTableWrapper,
    XTable,
    XTabs,
    XTab,
    XForm,
    XModal,
    XButton,
    XTitle,
    XToast,
    XInstancesSelect,
    AIcon: Icon,
  },
  data() {
    return {
      serverModal: {
        open: false,
        serverData: {},
        instanceName: '',
        connectionLabel: '',
        error: '',
        serverName: 'New Server',
        uuid: null,
        valid: false,
      },
      connectionLabelError: '',
      showConnectionLabelBorder: false,
      selectedServers: [],
      message: '',
      toastTimeout: 60000,
      advancedSettings: false,
      configValid: true,
      deleting: false, // whether or not the modal for deleting confirmation is displayed
      deleteEntities: false, // if 'deleting = true' and deleting was confirmed this means that
      // also the entities of the associated users should be deleted
    };
  },
  computed: {
    ...mapGetters({
      getAdapterById: 'getAdapterById',
      getClientsMap: 'getClientsMap',
      getInstancesMap: 'getInstancesMap',
      requireConnectionLabel: REQUIRE_CONNECTION_LABEL,
    }),
    ...mapState({
      loading(state) {
        return state.adapters.adapters.fetching;
      },
      allClients(state) {
        return state.adapters.clients;
      },
      isCyberarkVault(state) {
        return _get(state, 'configuration.data.global.cyberark_vault', false);
      },
      connectionLabelValid() {
        return !this.requireConnectionLabel || this.serverModal.connectionLabel;
      },
    }),
    cannotOpenAdvancesSettings() {
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
    title() {
      return this.currentAdapter.title;
    },
    adapterLink() {
      return this.currentAdapter.link;
    },
    adapterClients() {
      const clients = _get(this.currentAdapter, 'clients', []);
      const instances = this.getInstancesMap;
      return clients.map((c) => {
        const client = this.getClientsMap.get(c);
        // eslint-disable-next-line camelcase
        const { node_id } = client;
        const instance = instances.get(node_id);

        return {
          ...client,
          ...client.client_config,
          node_name: instance.node_name,
        };
      });
    },
    instances() {
      const instancesIds = _get(this.currentAdapter, 'instances', []);
      const res = instancesIds.map((instance) => {
        const i = this.getInstancesMap.get(instance);
        return {
          name: i.node_id,
          title: i.node_name,
        };
      });

      return res;
    },
    instanceDefaultName() {
      if (!this.instances.length) return '';
      const instance = this.instances.find((i) => i.title === 'Master') || this.instances[0];
      return instance.name;
    },
    adapterSchema() {
      const currentSchema = _get(this.currentAdapter, 'schema', null);
      if (currentSchema) currentSchema.useVault = this.isCyberarkVault;
      return currentSchema;
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
    uploadFileEndpoint() {
      return `adapters/${this.adapterId}/${this.serverModal.instanceName}`;
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
  },
  async created() {
    this.fetchConfig();
    this.hintAdapterUp(this.adapterId);
    await this.lazyFetchAdapters();
    this.setDefaultInstance();
  },
  methods: {
    ...mapActions({
      lazyFetchAdapters: LAZY_FETCH_ADAPTERS,
      updateServer: SAVE_ADAPTER_CLIENT,
      testAdapter: TEST_ADAPTER_SERVER,
      archiveServer: ARCHIVE_CLIENT,
      updatePluginConfig: SAVE_PLUGIN_CONFIG,
      hintAdapterUp: HINT_ADAPTER_UP,
      fetchConfig: FETCH_SYSTEM_CONFIG,
    }),
    openHelpLink() {
      window.open(this.adapterLink, '_blank');
    },
    configConnection(clientId) {
      this.message = '';
      this.serverModal.valid = true;
      if (clientId === 'new') {
        this.serverModal = {
          ...this.serverModal,
          serverData: {},
          serverName: 'New Server',
          uuid: clientId,
          error: '',
          valid: false,
        };
      } else {
        const client = this.adapterClients.find((c) => c.uuid === clientId);
        this.serverModal = {
          ...this.serverModal,
          serverData: { ...client.client_config, oldInstanceName: client.node_id },
          instanceName: client.node_id,
          serverName: client.client_id,
          connectionLabel: client.client_config.connection_label,
          uuid: client.uuid,
          error: client.error,
          valid: true,
        };
        if (client.error && client.error !== '' && client.error.startsWith('cyberark_vault_error')) {
          const result = parseVaultError(client.error);
          this.serverModal.serverData[result[1]].error = result[2];
          this.serverModal.error = result[2];
        }
      }
      this.toggleServerModal();
    },
    removeConnection() {
      this.deleting = true;
    },
    async doRemoveServers() {
      for (const serverId of this.selectedServers) {
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
    onConnectionLabelInput() {
      if (this.requireConnectionLabel && this.serverModal.connectionLabel) {
        this.showConnectionLabelBorder = false;
        this.connectionLabelError = '';
      }
    },
    onConnectionLabelBlur() {
      this.showConnectionLabelBorder = !this.connectionLabelValid;
      this.connectionLabelError = this.connectionLabelValid ? '' : 'Connection Label is required';
    },
    saveServer() {
      this.message = 'Connecting to Server...';
      this.updateServer({
        adapterId: this.adapterId,
        client_id: this.serverModal.serverName,
        serverData: {
          ...this.serverModal.serverData,
          instanceName: this.serverModal.instanceName,
          connection_label: this.serverModal.connectionLabel,
        },
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
        serverData: { ...this.serverModal.serverData, instanceName: this.serverModal.instanceName },
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
    validateConfig(valid) {
      this.configValid = valid;
    },
    saveConfig(configName, config) {
      this.updatePluginConfig({
        pluginId: this.adapterId,
        configName,
        config,
      }).then(() => {
        this.message = 'Adapter configuration saved.';
        return true;
      });
    },
    toggleSettings() {
      if (this.advancedSettings) {
        this.$refs.tabs.$el.classList.add('shrinking-y');
        setTimeout(() => this.advancedSettings = false, 1000);
      } else {
        this.advancedSettings = true;
      }
    },
    setDefaultInstance() {
      this.serverModal.instanceName = this.instanceDefaultName;
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

    #connectionLabel.error-border {
      border: 1px solid $indicator-error;
    }
  }
</style>
