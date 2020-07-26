<template>
  <XPage title="devices">
    <XTable
      module="devices"
      @row-clicked="rowClicked"
    />
  </XPage>
</template>

<script>
import { mapActions } from 'vuex';
import XPage from '../axons/layout/Page.vue';
import XTable from '../networks/entities/Table.vue';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../store/modules/onboarding';
import { EXAMINE_DEVICE } from '../../constants/getting-started';

export default {
  name: 'XDevices',
  components: { XPage, XTable },
  methods: {
    ...mapActions({ milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION }),
    rowClicked() {
      this.milestoneCompleted({ milestoneName: EXAMINE_DEVICE });
    },
  },
};
</script>


<style lang="scss">
</style>
