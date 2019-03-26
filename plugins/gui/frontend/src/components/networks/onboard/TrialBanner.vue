<template>
  <div
    class="x-trial-banner"
    v-if="inTrial"
  >
    <template
      v-if="trialDaysRemaining <= 0"
    >
      <x-banner
        severity="error"
      >Axonius evaluation period has expired. Please reach out to your Account Manager.</x-banner>
      <div class="banner-overlay" />
    </template>
    <x-banner
      v-else-if="trialDaysRemaining <= 7"
      severity="error"
    >{{ trialDaysRemaining }} {{unit}} remaining in your Axonius evaluation</x-banner>
    <x-banner
      v-else-if="trialDaysRemaining <= 14"
      severity="warning"
    >{{ trialDaysRemaining }} {{unit}} remaining in your Axonius evaluation</x-banner>
    <x-banner
      v-else
      severity="info"
    >{{ trialDaysRemaining }} {{unit}} remaining in your Axonius evaluation</x-banner>
  </div>
</template>

<script>
  import xBanner from '../../axons/popover/Banner.vue'
  import featureFlagsMixin from '../../../mixins/feature_flags'

  import {mapState} from 'vuex'

  export default {
    name: 'XTrialBanner',
    components: {
      xBanner
    },
    mixins: [featureFlagsMixin],
    computed: {
      ...mapState({
        isAxonius (state) {
          return state.auth.currentUser.data.user_name === '_axonius'
        }
      }),
      trialDaysRemaining () {
        if (!this.featureFlags || !this.featureFlags.trial_end) return null
        return Math.ceil((new Date(this.featureFlags.trial_end) - new Date()) / 1000 / 60 / 60 / 24)
      },
      inTrial() {
        return this.trialDaysRemaining !== null && !this.isAxonius
      },
      unit() {
        if (this.trialDaysRemaining === 1) {
          return 'day'
        }
        return 'days'
      }
    }
  }
</script>

<style lang="scss">

</style>