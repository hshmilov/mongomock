<template>
  <div class="x-tunnel tab-settings">
    <XButton
      class="tunnel-status-btn"
      :icon="checkButtonObject.icon"
      :class="checkButtonObject.class"
      size="large"
      @click="checkTunnelStatus"
    >
      {{ checkButtonObject.text }}
    </XButton>
    <ASteps
      direction="vertical"
      class="tunnel-steps"
    >
      <AStep
        status="process"
      >
        <template #title>
          <div class="step-title">
            Tunnel proxy configuration
            <div class="hint">
              optional
            </div>
          </div>
          <XButton
            type="link"
            class="help-link"
            title="More information about Tunnel proxy configuration"
            @click="openHelpLink"
          >
            <XIcon
              type="question-circle"
            />
            Help
          </XButton>
        </template>
        <template slot="description">
          <div class="step-sub-title">
            Configure a proxy for the Tunnel
          </div>
          <XForm
            v-model="proxySettings"
            :schema="proxySchema"
            silent
            @validate="onFormValidate"
          />
        </template>
      </AStep>
      <AStep
        status="process"
      >
        <template #title>
          <div class="step-title">
            Tunnel installation
          </div>
          <XButton
            type="link"
            class="help-link"
            title="More information about Tunnel proxy configuration"
            @click="openHelpLink"
          >
            <XIcon
              type="question-circle"
            />
            Help
          </XButton>
        </template>
        <template slot="description">
          <ol class="tunnel-ordered-list">
            <li>
              Provision a server that meets the following network
              requirements either by direct connection or by HTTPS proxy:
              <ul class="tunnel-unordered-list">
                <li>Access to the internet via TCP port 443.</li>
                <li>
                  Access to the sources of the adapters that will be
                  connected using this tunnel.
                </li>
              </ul>
            </li>
            <li>Install <a
              href="https://releases.ubuntu.com/16.04/"
              target="_blank"
            >Ubuntu 16.04</a> on the server.</li>
            <li>
              Install the <a
                href="https://docs.docker.com/engine/install/ubuntu/"
                target="_blank"
              >Docker Engine</a>
              software on the Ubuntu 16.04 server.
            </li>
            <li>
              Click the <strong>Download Tunnel</strong>
              button below to download the installation package.
            </li>
            <li>Copy the installation package to your server.</li>
            <li>
              Execute the installation package as the "root" user. For example:
              <ul class="tunnel-unordered-list">
                <li><code>chmod +x axonius_tunnel_launcher.sh</code></li>
                <li><code>./axonius_tunnel_launcher.sh</code></li>
              </ul>
            </li>
            <li>
              When the installation package has finished successfully it will show the
              following message: "The Axonius Tunnel has been successfully installed".
            </li>
            <li>
              After the installation finishes, refresh this page and the
              <strong>Tunnel Status</strong>
              button in the upper right corner of this screen will display
              <strong>Connected</strong>.
            </li>
          </ol>
          <XButton
            class="tunnel-download-btn"
            size="large"
            :disabled="!canBeDownloaded"
            @click="downloadTunnel"
          >
            Download Tunnel
          </XButton>
        </template>
      </AStep>
      <AStep
        status="process"
      >
        <template #title>
          <div class="step-title">
            Tunnel status notification
            <div class="hint">
              optional
            </div>
          </div>
        </template>
        <template slot="description">
          <div class="step-sub-title">
            Send email to the following recipients if the Tunnel disconnects
          </div>
          <XArrayEdit
            v-model="mailSettings"
            :read-only="cannotUpdateTunnelSettings"
            :schema="mailSchema"
            @validate="onValidate"
          />
          <XButton
            type="primary"
            :disabled="saveButtonDisabled"
            @click="saveConfig"
          >
            Save
          </XButton>
        </template>
      </AStep>
    </ASteps>
    <XToast
      v-if="message"
      v-model="message"
      :timeout="5000"
    />
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { Steps } from 'ant-design-vue';
import XButton from '@axons/inputs/Button.vue';
import XToast from '@axons/popover/Toast.vue';
import XIcon from '@axons/icons/Icon';
import {
  GET_TUNNEL_STATUS,
  SAVE_TUNNEL_EMAILS_LIST,
  GET_TUNNEL_EMAILS_LIST,
  SAVE_TUNNEL_PROXY_SETTINGS,
  GET_TUNNEL_PROXY_SETTINGS,
} from '@store/actions';
import { emptyScheme } from '@constants/settings';
import XArrayEdit from '@neurons/schema/types/array/ArrayEdit.vue';
import XForm from '@neurons/schema/Form.vue';
import _isEqual from 'lodash/isEqual';
import _get from 'lodash/get';

export default {
  name: 'XTunnel',
  components: {
    XButton,
    XArrayEdit,
    XToast,
    XForm,
    XIcon,
    ASteps: Steps,
    AStep: Steps.Step,
  },
  data() {
    return {
      tunnelStatus: false,
      formValid: true,
      emailValid: true,
      message: '',
      proxySettings: {
        enabled: false,
        tunnel_proxy_addr: '',
        tunnel_proxy_port: 8080,
        tunnel_proxy_user: '',
        tunnel_proxy_password: '',
      },
      originalSettings: {},
      mailSettings: {
        emailList: [],
      },
    };
  },
  computed: {
    ...mapState({
      tunnelSchema(state) {
        const items = _get(state, 'settings.configurable.core.CoreService.schema.items');
        return items ? items.find((item) => item.name === 'tunnel_settings') : false;
      },
    }),
    proxySchema() {
      if (this.tunnelSchema) {
        return this.tunnelSchema.items[1];
      }
      return { ...emptyScheme };
    },
    mailSchema() {
      return {
        name: 'mail_config',
        title: '',
        items: [
          {
            name: 'emailList',
            type: 'array',
            items: {
              type: 'string',
              format: 'email',
            },
          },
        ],
        type: 'array',
      };
    },
    cannotUpdateTunnelSettings() {
      return this.$cannot(
        this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update,
      ) || !this.formValid;
    },
    canBeDownloaded() {
      return _isEqual(this.originalSettings, this.proxySettings);
    },
    checkButtonObject() {
      if (this.tunnelStatus === 'True') {
        return {
          icon: 'check-circle',
          class: 'tunnel-success',
          text: 'Connected',
        };
      }
      if (this.tunnelStatus === 'False') {
        return {
          icon: 'warning',
          class: 'tunnel-error',
          text: 'Disconnected',
        };
      }
      return {
        icon: 'loading',
        class: 'tunnel-loading',
        text: 'Loading...',
      };
    },
    saveButtonDisabled() {
      if (!this.tunnelSchema) {
        return true;
      }
      return this.cannotUpdateTunnelSettings || !this.emailValid;
    },
  },
  async mounted() {
    const proxySettings = await this.getTunnelProxySettings();
    this.proxySettings = proxySettings.data;
    this.originalSettings = proxySettings.data;
    const emailsList = await this.getTunnelEmailsList();
    this.mailSettings.emailList = emailsList.data ? emailsList.data : [];
    const status = await this.getTunnelStatus();
    this.tunnelStatus = status.data;
  },
  methods: {
    ...mapActions({
      getTunnelStatus: GET_TUNNEL_STATUS,
      saveTunnelEmailsList: SAVE_TUNNEL_EMAILS_LIST,
      getTunnelEmailsList: GET_TUNNEL_EMAILS_LIST,
      saveTunnelProxySettings: SAVE_TUNNEL_PROXY_SETTINGS,
      getTunnelProxySettings: GET_TUNNEL_PROXY_SETTINGS,
    }),
    onFormValidate(valid) {
      this.formValid = valid;
    },
    async saveConfig() {
      let saved = false;
      this.message = '';
      if (this.emailValid) {
        await this.saveTunnelEmailsList(this.mailSettings.emailList)
          .then(() => { saved = true; })
          .catch(() => {
            this.message = 'A problem occured while trying to save the tunnel settings';
          });
      }
      if (this.formValid && !this.message) {
        await this.saveTunnelProxySettings(this.proxySettings)
          .then(() => { saved = true; })
          .catch(() => {
            this.message = 'A problem occured while trying to save the tunnel settings';
          });
      }
      if (saved) {
        if (!this.message) {
          this.message = 'Tunnel settings saved successfully';
        }
        this.originalSettings = this.proxySettings;
      }
    },
    openHelpLink() {
      window.open('https://docs.axonius.com/docs/installing-axonius-tunnel', '_blank');
    },
    downloadTunnel() {
      window.open('/api/tunnel/download_agent', '_blank');
    },
    async checkTunnelStatus() {
      this.tunnelStatus = false;
      const status = await this.getTunnelStatus();
      this.tunnelStatus = status.data;
    },
    onValidate(field) {
      this.emailValid = field.valid;
    },
  },
};
</script>

<style lang="scss">
  .x-tunnel {
    width: 100%;
    position: relative;
    .x-array-edit {
      .object {
        width: 100%;
      }
    }
    .tunnel-status-btn {
      position: absolute;
      top: 0;
      right: 0;
      z-index: 10;
      width: 160px;
      display: flex;
      align-items: center;
      svg {
        fill: $theme-orange;
      }
      i + span {
        margin-left: 15px;
      }
      &.tunnel-success {
        color: $indicator-success;
        border-color: $indicator-success;
        svg {
          fill: $indicator-success;
        }
      }
      &.tunnel-error {
        color: $indicator-error;
        border-color: $indicator-error;
        svg {
          fill: $indicator-error;
        }
      }
    }
    .tunnel-steps {
      .ant-steps-item-tail::after {
        background-color: $theme-blue;
        width: 2px;
      }
      .ant-steps-item-icon {
        border: 0;
        background-color: rgba($theme-blue, 0.08);
        .ant-steps-icon {
          color: $theme-black;
          font-weight: normal;
        }
      }
      .ant-steps-item-title {
        color: $theme-black;
        font-weight: 400;
        .step-title {
          display: inline-block;
        }
        .hint {
          font-weight: 100;
          text-shadow: 0 0 0 $theme-black;
        }
        .help-link {
          display: inline-flex;
          align-items: center;
          vertical-align: middle;
          i {
            font-size: 20px;
          }
        }
      }
      .ant-steps-item-description {
        color: $theme-black;
        .step-sub-title {
          margin-bottom: 10px;
        }
        .tunnel-ordered-list {
          .tunnel-unordered-list {
            list-style: disc;
            padding-left: 24px;
          }
          a {
            &, &:visited, &:hover, &:active {
              color: $theme-blue;
              text-decoration: none;
            }
            &:hover {
              text-decoration: underline;
            }
          }
          code {
            background-color: #f5f5f5;
            color: $theme-black;
            box-shadow: none;
            font-weight: normal;
          }
        }
        .tunnel-download-btn:not([disabled]) {
          color: $theme-blue;
          background-color: $theme-white;
          border-color: $theme-blue;
        }
        > .x-array-edit {
          margin-bottom: 30px;
        }
      }
    }
  }
</style>
