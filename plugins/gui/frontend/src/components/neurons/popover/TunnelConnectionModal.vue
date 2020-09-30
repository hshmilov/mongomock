<template>
  <AModal
    :visible="tunnelDisconnected"
    :mask-closable="false"
    :z-index="9999"
    :footer="null"
    :centered="true"
    class="tunnel-modal"
    @cancel="dismissModal"
  >
    <template>
      <div class="tunnel-modal-header">
        <XIcon
          type="close-circle"
          theme="filled"
        />
        Tunnel is disconnected!
      </div>
      <div class="tunnel-modal-content">
        <div>
          Axonius is unable to connect to the Tunnel and will not be able to use it
          to fetch data from the source of this adapter. Please check the
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
        </div>
      </div>
    </template>
  </AModal>
</template>

<script>
import { Modal } from 'ant-design-vue';
import { mapMutations, mapState } from 'vuex';
import { TOGGLE_TUNNEL_CONNECTION_MODAL } from '@store/modules/dashboard';

export default {
  name: 'XTunnelConnectionModal',
  components: {
    AModal: Modal,
  },
  computed: {
    ...mapState({
      tunnelDisconnected(state) {
        return state.dashboard.tunnelDisconnected;
      },
    }),
    canGoToTunnelSettings() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update);
    },
  },
  methods: {
    ...mapMutations({
      dismissModal: TOGGLE_TUNNEL_CONNECTION_MODAL,
    }),
    goToTunnelSettings() {
      this.dismissModal();
      this.$router.push({ path: '/settings/#tunnel-settings-tab' });
    },
  },
};
</script>

<style lang="scss">
.ant-modal-root {
  .ant-modal-wrap {
    .ant-modal.tunnel-modal {
      .ant-modal-content {
        width: 465px;
        .ant-modal-body {
          padding: 30px;
          .tunnel-modal-header {
            margin-bottom: 30px;
            font-weight: 500;
            color: $indicator-error;
            fill: $indicator-error;
            .x-icon {
              margin-right: 10px;
            }
          }
          .tunnel-modal-content {
            .x-button {
              padding: 0;
              height: 20px;
              &:hover {
                span {
                  text-decoration: underline;
                }
              }
            }
          }
        }
      }
    }
  }
}
</style>
