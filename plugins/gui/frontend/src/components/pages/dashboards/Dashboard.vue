<template>
  <XPage title="axonius dashboard">
    <div
      v-if="loadWhileFetchSystemState"
      class="dashboard-spin-container"
    >
      <ASpin
        size="large"
      />
    </div>
    <XEmptySystem v-else-if="isStateEmpty" />
    <template v-else>
      <XSearchInsights
        v-if="canViewAnyEntity"
        @search="showInsights"
      />
      <XDashboardSpaces />
    </template>
  </XPage>
</template>

<script>
import { entities } from '@constants/entities';
import { Spin } from 'ant-design-vue';
import XPage from '@axons/layout/Page.vue';
import XEmptySystem from '@networks/onboard/EmptySystem.vue';
import XSearchInsights from '@neurons/inputs/SearchInsights.vue';
import { isEmptySystem } from '@api/dashboard';
import XDashboardSpaces from './DashboardSpaces.vue';


export default {
  name: 'XDashboard',
  components: {
    XPage,
    XEmptySystem,
    XSearchInsights,
    ASpin: Spin,
    XDashboardSpaces,
  },
  data() {
    const canViewAnyEntity = entities.some((entity) => this.$canViewEntity(entity.name));
    return {
      isStateEmpty: true,
      loadWhileFetchSystemState: true,
      canViewAnyEntity,
    };
  },
  async created() {
    const isEmpty = await isEmptySystem();
    this.loadWhileFetchSystemState = false;
    if (isEmpty) {
      // initiate repeatedly check if system state changed (active discovery)
      this.fetchSystemState();
    } else {
      this.isStateEmpty = false;
    }
  },
  destoryed() {
    clearTimeout(this.timer);
  },
  methods: {
    fetchSystemState() {
      this.timer = setTimeout(async () => {
        const empty = await isEmptySystem();
        if (empty) {
          this.fetchSystemState();
        } else {
          this.isStateEmpty = false;
          clearTimeout(this.timer);
        }
      }, 20000);
    },
    showInsights(search) {
      this.$router.push({
        name: 'Insights Explorer',
        query: {
          search,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
  .dashboard-spin-container {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }
</style>
