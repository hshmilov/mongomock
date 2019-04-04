<template>
  <div
    v-if="inTrial"
    class="x-trial-banner"
  >
    <template v-if="isExpired">
      <x-banner severity="error">Axonius evaluation period has expired. Please reach out to your Account Manager.</x-banner>
      <div class="banner-overlay" />
    </template>
    <x-banner
      v-else
      :severity="severity"
    >{{ trialDaysRemaining }} {{unit}} remaining in your Axonius evaluation</x-banner>
  </div>
</template>

<script>
  import xBanner from '../../axons/popover/Banner.vue'
  import featureFlagsMixin from '../../../mixins/feature_flags'

  import {mapState, mapGetters} from 'vuex'
  import {IS_EXPIRED} from '../../../store/getters'

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
      ...mapGetters({
        isExpired: IS_EXPIRED
      }),
      trialDaysRemaining () {
        if (!this.featureFlags || !this.featureFlags.trial_end) return null
        
        let expirationDate = new Date(this.featureFlags.trial_end)
        expirationDate.setMinutes(expirationDate.getMinutes() - expirationDate.getTimezoneOffset())
        return Math.ceil((expirationDate - new Date()) / 1000 / 60 / 60 / 24)
      },
      inTrial() {
        return this.trialDaysRemaining !== null && !this.isAxonius
      },
      severity() {
        if (this.trialDaysRemaining <= 7) return 'error'
        if (this.trialDaysRemaining <= 14) return 'warning'
        return 'info'
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