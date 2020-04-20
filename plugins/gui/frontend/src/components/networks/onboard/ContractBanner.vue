<template>
  <div
    v-if="inContract"
    class="x-contract-banner"
  >
    <template v-if="isExpired || contractDaysRemaining < 1">
      <XBanner severity="error">
        Your Axonius subscription has expired. <a href="mailto:sales@axonius.com?subject=Axonius subscription is about to expire&amp;body=Please contact me for renewal options"><u style="color: white;">Contact us</u></a> for renewal option
      </XBanner>
      <div
        v-if="isExpired"
        class="banner-overlay"
      />
    </template>
    <XBanner
      v-else
      :severity="severity"
    >Your Axonius subscription expires in {{ contractDaysRemaining }} {{ unit }}. Please <a href="mailto:sales@axonius.com?subject=Axonius subscription is about to expire&amp;body=Please contact me for renewal options"><u style="color: white;">contact us</u></a>{{ suffix }}</XBanner>
  </div>
</template>

<script>
import dayjs from 'dayjs';
import { serverTime } from '@api/axios';
import _get from 'lodash/get';
import { mapState, mapGetters } from 'vuex';
import XBanner from '../../axons/popover/Banner.vue';
import { IS_EXPIRED } from '../../../store/getters';

export default {
  name: 'XContractBanner',
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
    contractDaysRemaining() {
      let now = dayjs();
      if (this.isContractDefined) {
        if (serverTime) {
          // Calculates the date relative to the server time and not the browser time
          now = dayjs(serverTime);
        }
        const expiry_date = dayjs(this.featureFlags.expiry_date);
        return expiry_date.diff(now, 'days');
      }
    },
    isContractDefined() {
      return this.featureFlags && this.featureFlags.expiry_date;
    },
    inContract() {
      return this.isContractDefined && !this.$isAxoniusUser() && this.contractDaysRemaining <= 60;
    },
    severity() {
      if (this.contractDaysRemaining < 4) return 'verydangerous';
      if (this.contractDaysRemaining < 16) return 'dangerous';
      return 'info';
    },
    unit() {
      if (this.contractDaysRemaining === 1) {
        return 'day';
      }
      return 'days';
    },
    suffix() {
      if (this.contractDaysRemaining < 4) return '';
      if (this.contractDaysRemaining < 16) return ' to avoid service disruption.';
      if (this.contractDaysRemaining <= 60) return ' for renewal options.';
    },
  },
};
</script>
