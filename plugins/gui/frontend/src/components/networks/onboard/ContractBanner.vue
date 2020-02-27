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
import moment from 'moment';
import { mapState, mapGetters } from 'vuex';
import XBanner from '../../axons/popover/Banner.vue';
import featureFlagsMixin from '../../../mixins/feature_flags';

import { IS_EXPIRED } from '../../../store/getters';

export default {
  name: 'XContractBanner',
  components: {
    XBanner,
  },
  mixins: [featureFlagsMixin],
  computed: {
    ...mapState({
      isAxonius(state) {
        return state.auth.currentUser.data.user_name === '_axonius';
      },
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
    }),
    contractDaysRemaining() {
      if (this.isContractDefined){
        const expiry_date = moment(this.featureFlags.expiry_date);
        return Math.ceil(moment.duration(expiry_date.diff(moment())).asDays());
      };
    },
    isContractDefined() {
      return this.featureFlags && this.featureFlags.expiry_date;
    },
    inContract() {
      return this.isContractDefined && !this.isAxonius && this.contractDaysRemaining <= 60;
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
