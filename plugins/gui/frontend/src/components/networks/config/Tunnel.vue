<template>
  <div class="x-tunnel tab-settings">
    <VStepper
      v-model="e6"
      vertical
    >
      <VStepperStep
        :complete="e6 > 1"
        step="1"
      >
        <div>Tunnel proxy configuration <div
          class="hint"
          style="font-weight: 100;"
        >
          optional
        </div></div>
        <small>Configure a proxy for the Tunnel<XButton
          type="link"
          class="help-link"
          title="More information about Tunnel proxy configuration"
          @click="openHelpLink"
        >
          <MdIcon>help_outline</MdIcon>Help
        </XButton></small>
      </VStepperStep>

      <VStepperContent step="1">
        <XForm
          v-model="proxy_settings"
          :schema="proxySchema"
          :error="prettyUserError"
          silent
          @validate="onFormValidate"
        />
      </VStepperContent>

      <VStepperStep
        :complete="e6 > 2"
        step="2"
      >
        Tunnel installation
        <small>Download your Tunnel connect toolkit<XButton
          type="link"
          class="help-link"
          title="More information about connecting the tunnel"
          @click="openHelpLink"
        >
          <MdIcon>help_outline</MdIcon>Help
        </XButton></small>
      </VStepperStep>

      <VStepperContent step="2">
        <VBtn
          v-if="!tunnel_status"
          outlined
          color="#727272"
          class="tunnel-status"
          dark
          @click="checkTunnelStatus"
        >
          <VProgressCircular
            indeterminate
            class="center-progress-bar"
            color="primary"
            size="16"
            width="2"
          />
          Checking...
        </VBtn>
        <VBtn
          v-if="tunnel_status === 'True'"
          outlined
          color="#2bcc71"
          class="tunnel-status"
          dark
          @click="checkTunnelStatus"
        ><svg
          id="prefix__Group_100"
          xmlns="http://www.w3.org/2000/svg"
          width="30"
          height="20"
          data-name="Group 100"
          viewBox="5 0 20 20"
        > <circle
          id="prefix__Ellipse_55"
          cx="10"
          cy="10"
          r="10"
          data-name="Ellipse 55"
          style="fill:#2bcc71"
        /> <path
          id="prefix__Path_10"
          d="M0 2.746L3.11 5.7 8.55 0"
          data-name="Path 10"
          transform="translate(6.113 7.334)"
          style="fill:none;stroke:#fff;stroke-miterlimit:10;stroke-width:2px"
        /> </svg>
          Connected
        </VBtn>
        <VBtn
          v-if="tunnel_status === 'False'"
          outlined
          color="#c02827"
          class="tunnel-status"
          dark
          @click="checkTunnelStatus"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="30"
            height="17.5"
            viewBox="5 0 20 17.5"
          > <g
            id="prefix__Group_102"
            data-name="Group 102"
            transform="translate(-1)"
          > <path
            id="prefix__Polygon_1"
            d="M10 0l10 17.5H0z"
            data-name="Polygon 1"
            transform="translate(1)"
            style="fill:#c02827"
          /> <text
            id="prefix___"
            data-name="!"
            transform="translate(10 14.5)"
            style="fill:#fff;font-size:8px;font-family:Roboto-Regular,Roboto"
          > <tspan
            x="0"
            y="0"
          >!</tspan> </text> </g> </svg>Disconnected
        </VBtn>

        <VBtn
          color="#0076ff"
          outlined
          href="/api/tunnel/download_agent"
          style="text-transform: none !important;"
          :disabled="!allDetailsFilled"
        >Download Tunnel
        </VBtn>
      </VStepperContent>

      <VStepperStep
        :complete="e6 > 3"
        step="3"
      >
        <div>Tunnel status notification <div
          class="hint"
          style="font-weight: 100;"
        >
          optional
        </div></div>
        <small>Send email to the following recipients if the Tunnel disconnects</small>
      </VStepperStep>

      <VStepperContent step="3">
        <XArrayEdit
          ref="mail_ref"
          v-model="mail_properties"
          :read-only="cannotUpdateTunnelSettings"
          :schema="mailSchema"
          @validate="onValidate"
        />
        <div>&nbsp;</div>
        <XButton
          type="primary"
          :disabled="cannotUpdateTunnelSettings"
          @click="saveConfig"
        >Save</XButton>
      </VStepperContent>
    </VStepper>
    <XToast
      v-if="message"
      v-model="message"
      :timeout="toastTimeout"
    />
  </div>
</template>

<script>
import { mapActions } from 'vuex';
import XButton from '@axons/inputs/Button.vue';
import XToast from '@axons/popover/Toast.vue';
import XArrayEdit from '../../neurons/schema/types/array/ArrayEdit.vue';
import XForm from '../../neurons/schema/Form.vue';
import configMixin from '../../../mixins/config';
import userErrorMixin from '../../../mixins/user_error';
import {
  GET_TUNNEL_STATUS, SAVE_TUNNEL_EMAILS_LIST, GET_TUNNEL_EMAILS_LIST, SAVE_TUNNEL_PROXY_SETTINGS, GET_TUNNEL_PROXY_SETTINGS,
} from '../../../store/actions';

export default {
  name: 'XTunnel',
  components: {
    XButton,
    XArrayEdit,
    XToast,
    XForm,
  },
  mixins: [configMixin, userErrorMixin],
  data() {
    return {
      e6: 1,
      tunnel_status: false,
      invalidForm: false,
      emailList: [],
      message: '',
      toastTimeout: 5000,
      download_enabled: false,
      items_loaded: 0,
      proxy_settings: {
        enabled: false,
        tunnel_proxy_addr: '',
        tunnel_proxy_port: 8080,
        tunnel_proxy_user: '',
        tunnel_proxy_password: '',
      },
      proxy_settings_items: [
        {
          name: 'enabled',
          title: 'Use proxy',
          type: 'bool',
        },
        {
          name: 'tunnel_proxy_addr',
          title: 'Proxy address',
          type: 'string',
        },
        {
          name: 'tunnel_proxy_port',
          title: 'Proxy port',
          type: 'number',
        },
        {
          name: 'tunnel_proxy_user',
          title: 'Proxy user name',
          type: 'string',
        },
        {
          name: 'tunnel_proxy_password',
          title: 'Proxy password',
          type: 'string',
          format: 'password',
        },
      ],
      requiredItems: ['enabled', 'tunnel_proxy_addr', 'tunnel_proxy_port'],
    };
  },
  computed: {
    proxySchema() {
      return {
        type: 'array',
        required: this.requiredItems,
        items: this.proxy_settings_items,
      };
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
            required: true,
          },
        ],
        required: [
          'emailList',
        ],
        type: 'array',
      };
    },
    cannotUpdateTunnelSettings() {
      return this.$cannot(
        this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update,
      ) || this.invalidForm;
    },
    allDetailsFilled() {
      return this.download_enabled;
    },
    mail_properties: {
      get() {
        if (this.emailList.emailList === 0 || this.emailList === [] || this.emailList === {}) {
          this.emailList = { emailList: [] };
        } else if ('emailList' in this.emailList === false) {
          this.emailList = { emailList: this.emailList };
        }
        return this.emailList;
      },
      set(newValue) {
        this.emailList = newValue;
      },
    },
  },
  async mounted() {
    const proxy_settings = await this.getTunnelProxySettings();
    this.proxy_settings = proxy_settings.data;
    this.upadteDownloadEnabledStatus();
    const emailsList = await this.getTunnelEmailsList();
    this.emailList = { emailList: emailsList.data };
    const status = await this.getTunnelStatus();
    this.tunnel_status = status.data;
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
      this.invalidForm = !valid;
      if (this.items_loaded > this.proxy_settings_items.length + 1) {
        this.download_enabled = false;
      }
      this.items_loaded += 1;
    },
    upadteDownloadEnabledStatus() {
      if (this.proxy_settings.enabled == false) {
        this.download_enabled = true;
      } else if (this.proxy_settings.tunnel_proxy_addr !== '' && !isNaN(this.proxy_settings.tunnel_proxy_port)) {
        this.download_enabled = true;
      }
    },
    async saveConfig() {
      if (this.emailList.length > 0 || this.emailList.emailList.length > 0) {
        this.checkEmptySettings('send_emails');
        if (this.anyEmptySettings) {
          return;
        }
      }
      await this.saveTunnelEmailsList(this.emailList.emailList).then(() => {}).catch(() => {
        this.message = 'A problem occured while trying to save the tunnel settings';
      });
      if (!this.invalidForm) {
        await this.saveTunnelProxySettings(this.proxy_settings).then(() => {}).catch(() => {
          this.message = 'A problem occured while trying to save the tunnel settings';
        });
      }
      this.upadteDownloadEnabledStatus();
      this.message = 'Tunnel settings saved successfully';
    },
    openHelpLink() {
      window.open('https://docs.axonius.com/docs/installing-axonius-tunnel', '_blank');
    },
    async checkTunnelStatus() {
      this.tunnel_status = false;
      const status = await this.getTunnelStatus();
      this.tunnel_status = status.data;
    },
    onValidate(field) {
      return field.valid;
    },
  },
};
</script>

<style lang="scss">
  .x-tunnel {
    width: 100%;
    .x-array-edit {
      .object {
        width: 100%;
      }
    }
    .v-stepper, .v-stepper__header {
      box-shadow: 0 0 0 0, 0 0 0, 0 0 0 0, 0 0 0;
    }
    .theme--light.v-stepper--vertical, .v-stepper__content:not(:last-child) {
      border-left: 0 !important;
      padding-top: 2px !important;
    }
    .v-stepper__wrapper {
      height: auto !important;
    }
    .v-stepper__step__step, .v-stepper__step__step.primary{
      color: black !important;
      background-color: #f4f6fc !important;
      border-color: black !important;
    }
    .v-stepper__label {
      text-shadow: 0 0 0 #000;
      font-weight: 400;
      font-size: 16px;
    }
    small {
      font-size: 14px;
      font-weight: 200;
      color: black !important;
      margin-top: 0.5em;
    }
    .help-link {
      padding-right: 0;
      position: absolute;
      margin-top: -0.5em;
      i {
        font-size: 20px!important;
      }
    }
    .tunnel-status {
      position: absolute;
      right: 2em;
      top: 2em;
      text-transform: none !important;
      font-family: Roboto;
      font-size: 14px;
      font-weight: normal;
    }
    .center-progress-bar {
      margin-right: 0.5em;
    }
  }
</style>
