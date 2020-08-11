<template>
  <div class="tunnel-connection-message">
    <div
      v-if="showConfigureTunnel"
    >
      If the source for this adapter is only accessible by an internal network,
      you must configure and install a Tunnel on a server that has access to the source.
      <XButton
        :disabled="!canGoToTunnelSettings"
        type="primary"
        @click="goToTunnelSettings"
      >
        Tunnel Installation Instructions
      </XButton>
    </div>
    <div
      v-else-if="showConfigureUseTunnel"
    >
      If the source for this adapter is only accessible by an internal network,
      you must enable the <strong>Use Tunnel to connect to source</strong> checkbox in the
      <strong>Adapter Configuration</strong> tab of the
      <XButton
        v-if="canOpenAdvancedSettings"
        type="link"
        @click="openAdvanceSettings"
      >
        Advanced Settings
      </XButton>
      <span v-else>
        Advanced Settings
      </span>
      for this adapter.
    </div>
    <div
      v-else-if="showTunnelError"
      class="tunnel-error-text"
    >
      <span>
        <XIcon
          type="close-circle"
          theme="filled"
        />
      </span>
      <span>
        Axonius is unable to connect to the Tunnel and will not be able to use it
        to fetch data from the source of this adapter. <br> Please check the
        <XButton
          v-if="canGoToTunnelSettings"
          type="link"
          @click="goToTunnelSettings"
        >
          Tunnel Settings
        </XButton>
        <span
          v-else
        >
          Tunnel Settings
        </span>
        page for more information.
      </span>
    </div>
  </div>
</template>

<script>
import { tunnelConnectionStatuses } from '@constants/settings';
import XIcon from '@axons/icons/Icon';
import XButton from '@axons/inputs/Button.vue';

export default {
  name: 'XAdapterTunnelConnectionMessage',
  components: { XButton, XIcon },
  props: {
    status: {
      type: String,
      default: '',
    },
    useTunnelSetting: {
      type: Boolean,
      default: undefined,
    },
  },
  computed: {
    showConfigureTunnel() {
      return (this.status === tunnelConnectionStatuses.neverConnected
              || (this.status === tunnelConnectionStatuses.disconnected
              && this.useTunnelSetting === false));
    },
    showConfigureUseTunnel() {
      return this.status === tunnelConnectionStatuses.connected && this.useTunnelSetting === false;
    },
    showTunnelError() {
      return this.status === tunnelConnectionStatuses.disconnected && this.useTunnelSetting;
    },
    canGoToTunnelSettings() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update);
    },
    canOpenAdvancedSettings() {
      return this.$can(this.$permissionConsts.categories.Adapters,
        this.$permissionConsts.actions.Update);
    },
  },
  methods: {
    goToTunnelSettings() {
      this.$router.push({ path: '/settings/#tunnel-settings-tab' });
    },
    openAdvanceSettings() {
      this.$emit('open-settings');
    },
  },
};
</script>

<style lang="scss">
.tunnel-connection-message {
  min-height: 22px;
  .x-button {
    &.ant-btn-primary {
      width: auto;
      margin-left: 10px;
    }
    &.ant-btn-link {
      height: 20px;
      padding: 0;
      &:hover {
        span {
          text-decoration: underline;
        }
      }
    }
  }
  .tunnel-error-text {
    color: $indicator-error;
    fill: $indicator-error;
    .x-button {
      color: $indicator-error;
      &:hover {
        span {
          text-decoration: underline;
        }
      }
    }
    > span {
      display: inline-block;
      vertical-align: top;
      &:first-child {
        margin-right: 5px;
      }
    }
  }
}
</style>
