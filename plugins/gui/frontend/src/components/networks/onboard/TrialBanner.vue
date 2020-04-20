<template>
  <div
    v-if="inTrial"
    class="x-trial-banner"
  >
    <template v-if="isExpired || trialDaysRemaining < 1">
      <XBanner severity="error">Axonius evaluation period has expired. Please reach out to your Account Manager.</XBanner>
      <div
        v-if="withOverlay"
        class="banner-overlay"
      />
    </template>
    <XBanner
      v-else
      :severity="severity"
    >{{ trialDaysRemaining }} {{ unit }} remaining in your Axonius evaluation</XBanner>
  </div>
</template>

<script>
import { mapState, mapGetters } from 'vuex';
import _get from 'lodash/get';
import XBanner from '../../axons/popover/Banner.vue';

import { IS_EXPIRED } from '../../../store/getters';

export default {
  name: 'XTrialBanner',
  components: {
    XBanner,
  },
  computed: {
    ...mapState({
      featureFlags(state) {
        const featureFlasConfigs = _get(state, 'settings.configurable.gui.FeatureFlags.config', null);
        return featureFlasConfigs;
      },
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
    }),
    // until https://axonius.atlassian.net/browse/AX-6369
    // we check here if the requested page in the administration
    // and prevent the expired overlay from this page
    withOverlay() {
      return this.$route.path !== '/administration';
    },
    trialDaysRemaining() {
      if (!this.featureFlags || !this.featureFlags.trial_end) return null;

      const expirationDate = new Date(this.featureFlags.trial_end);
      expirationDate.setMinutes(expirationDate.getMinutes() - expirationDate.getTimezoneOffset());
      return Math.ceil((expirationDate - new Date()) / 1000 / 60 / 60 / 24);
    },
    inTrial() {
      return this.trialDaysRemaining !== null && !this.$isAxoniusUser();
    },
    severity() {
      if (this.trialDaysRemaining <= 7) return 'error';
      if (this.trialDaysRemaining <= 14) return 'warning';
      return 'info';
    },
    unit() {
      if (this.trialDaysRemaining === 1) {
        return 'day';
      }
      return 'days';
    },
  },
};
</script>

<style lang="scss">

</style>
