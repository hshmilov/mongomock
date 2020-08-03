<template>
  <XPage
    title="instances"
    class="x-instances"
  >
    <XTableWrapper
      title="Edit, Deactivate or Reactivate Instances"
      :loading="loading"
    >
      <template slot="actions">
        <XButton
          id="get-connection-string"
          type="primary"
          :disabled="!canEditInstances"
          @click="connecting= !connecting"
        >Connect Node</XButton>
      </template>
      <XTable
        v-if="instances"
        slot="table"
        v-model="selectedInstance"
        id-field="node_id"
        :data="instances"
        :fields="fields"
        :on-click-row="showNameChangeModal"
        :multiple-row-selection="canEditInstances"
      />
    </XTableWrapper>
    <XInstanceSidePanel
      :instance.sync="sidePanelInstance"
      :visible="isSidePanelVisible"
      :disabled="!canEditInstances"
      @close="closeSidePanel"
      @deactivate="deactivateServers"
      @reactivate="reactivateServers"
      @save="instanceNameChange"
    />
    <XModal
      v-if="connecting && canEditInstances"
      @close="connecting= !connecting"
      @confirm="connecting= !connecting"
    >
      <div slot="body">How to connect a new node<br><br>
        1. Deploy another Axonius machine on the required subnet.<br>
        2. Log in to that machine via ssh with these credentials: node_maker:M@ke1tRain<br>
        3. Paste a connection string that looks like (with spaces)
        : {{ hostIP }} {{ connectionEncriptionKey }} &lt;User-Nickname&gt;
      </div>
      <div slot="footer">
        <XButton
          type="primary"
          @click="connecting= !connecting"
        >
          OK
        </XButton>
      </div>
      <button>Copy To Clipboard</button>
    </XModal>
  </XPage>
</template>

<script>
import { mapMutations, mapActions } from 'vuex';
import XInstanceSidePanel from '@networks/instances/InstanceSidePanel.vue';
import XPage from '../axons/layout/Page.vue';
import XTableWrapper from '../axons/tables/TableWrapper.vue';
import XTable from '../axons/tables/Table.vue';
import XButton from '../axons/inputs/Button.vue';
import XModal from '../axons/popover/Modal/index.vue';

import { REQUEST_API } from '../../store/actions';
import { SHOW_TOASTER_MESSAGE, UPDATE_FOOTER_MESSAGE } from '../../store/mutations';

export default {
  name: 'XInstances',
  components: {
    XPage, XTableWrapper, XTable, XButton, XModal, XInstanceSidePanel,
  },
  data() {
    return {
      loading: true,
      selectedInstance: [],
      instances: null,
      connecting: false,
      machineIP: '',
      connectionKey: '',
      isSidePanelVisible: false,
      sidePanelInstance: null,
    };
  },
  computed: {
    canEditInstances() {
      return this.$can(this.$permissionConsts.categories.Instances,
        this.$permissionConsts.actions.Update);
    },
    fields() {
      return [
        { name: 'node_name', title: 'Name', type: 'string' },
        { name: 'hostname', title: 'Hostname', type: 'string' },
        {
          name: 'ips', title: 'IP', type: 'array', items: { type: 'string' },
        },
        {
          name: 'last_seen', title: 'Last Seen', type: 'string', format: 'date-time',
        },
        { name: 'status', title: 'Status', type: 'string' },
        { name: 'node_user_password', title: 'Instance Connect User Password', type: 'string' },
      ];
    },
    hostIP() {
      return this.machineIP;
    },
    connectionEncriptionKey() {
      return this.connectionKey;
    },
    showActivationOption() {
      if (!this.selectedInstance || this.selectedInstance.length !== 1) return '';
      const selectedInstance = this.instances
        .find((instance) => instance.node_id === this.selectedInstance[0]);
      return selectedInstance.status;
    },

  },
  methods: {
    ...mapMutations({
      showToasterMessage: SHOW_TOASTER_MESSAGE,
      updateFooterMessage: UPDATE_FOOTER_MESSAGE,
    }),
    ...mapActions({
      fetchData: REQUEST_API,
    }),
    instanceNameChange() {
      this.fetchData({
        rule: 'instances',
        method: 'POST',
        data: {
          nodeIds: this.sidePanelInstance.nodeIds,
          node_name: this.sidePanelInstance.node_name,
          hostname: this.sidePanelInstance.hostname,
          use_as_environment_name: this.sidePanelInstance.use_as_environment_name,
        },
      }).then(() => {
        this.loading = true;
        this.loadData();
        this.updateFooterMessage(this.sidePanelInstance.use_as_environment_name
          ? this.sidePanelInstance.node_name : '');
        this.closeSidePanel();
      }).catch((errorResponse) => {
        this.showToasterMessage({ message: errorResponse.response.data.message });
        this.closeSidePanel();
      });
    },
    showNameChangeModal(instanceId) {
      const currentInstance = this.instances.find((instance) => instance.node_id === instanceId);
      this.sidePanelInstance = { ...currentInstance };
      this.sidePanelInstance.nodeIds = instanceId;
      this.selectedInstance = [instanceId];
      this.isSidePanelVisible = true;
    },
    deactivateServers() {
      if (!this.canEditInstances) return;
      this.$safeguard.show({
        text: `
                  Are you sure you want to deactivate this instance?<br/><br/>
                  This will remove all the adapter connections utilizing this instance.
                  `,
        confirmText: 'Deactivate',
        onConfirm: () => {
          this.closeSidePanel();
          this.doDeactivateServers();
        },
      });
    },
    reactivateServers() {
      if (!this.canEditInstances) return;
      this.$safeguard.show({
        text: `
                  Are you sure you want to reactivate this instance?<br/>
                  `,
        confirmText: 'Reactivate',
        onConfirm: () => {
          this.closeSidePanel();
          this.doReactivateServers();
        },
      });
    },
    doReactivateServers() {
      this.fetchData({
        rule: 'instances',
        method: 'POST',
        data: { nodeIds: this.selectedInstance[0], status: 'Activated' },
      }).then(() => this.loadData());
    },
    doDeactivateServers() {
      this.fetchData({
        rule: 'instances',
        method: 'DELETE',
        data: { nodeIds: this.selectedInstance },
      }).then(() => {
        this.loadData();
      }).catch((errorResponse) => {
        this.showToasterMessage({ message: errorResponse.response.data.message });
      });
    },
    loadData() {
      this.fetchData({
        rule: 'instances',
        method: 'GET',
      }).then((response) => {
        if (response.data) {
          this.instances = response.data.instances;
          this.machineIP = response.data.connection_data.host;
          this.connectionKey = response.data.connection_data.key;
          this.loading = false;
        }
      });
    },
    closeSidePanel() {
      this.isSidePanelVisible = false;
    },
  },
  async created() {
    this.loadData();
  },
};
</script>

<style lang="scss">
  .x-instances {
    .x-modal .modal-container {
      position: relative;
      width: auto;
    }
  }
</style>
