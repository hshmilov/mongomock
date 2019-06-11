<template>
  <x-page title="axonius dashboard">
    <template v-if="isEmptySystem === null" />
    <template v-else-if="isEmptySystem">
      <x-empty-system />
    </template>
    <template v-else>
      <x-search-insights @click="onClickInsights" />
      <x-spaces :spaces="spaces" />
    </template>
  </x-page>
</template>


<script>
  import xPage from '../axons/layout/Page.vue'
  import xEmptySystem from '../networks/onboard/EmptySystem.vue'
  import xSearchInsights from '../neurons/inputs/SearchInsights.vue'
  import xSpaces from '../networks/dashboard/Spaces.vue'

  import {
    FETCH_DISCOVERY_DATA, FETCH_DASHBOARD_SPACES, FETCH_DASHBOARD_FIRST_USE
  } from '../../store/modules/dashboard'
  import { IS_EXPIRED } from '../../store/getters'
  import { FETCH_DATA_VIEWS, SAVE_VIEW } from '../../store/actions'
  import { CHANGE_TOUR_STATE, NEXT_TOUR_STATE } from '../../store/modules/onboarding'
  import { IS_ENTITY_RESTRICTED, IS_ENTITY_EDITABLE } from '../../store/modules/auth'
  import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'

  export default {
    name: 'XDashboard',
    components: {
      xPage, xEmptySystem, xSearchInsights, xSpaces
    },
    computed: {
      ...mapState({
        dashboard (state) {
          return state.dashboard
        },
        spaces (state) {
          return state.dashboard.spaces.data
        },
        devicesView (state) {
          return state.devices.view
        },
        devicesViewsList (state) {
          return state.devices.views.saved.data
        },
        dashboardFirstUse (state) {
          return state.dashboard.firstUse.data
        }
      }),
      ...mapGetters({
        isExpired: IS_EXPIRED, isEntityRestricted: IS_ENTITY_RESTRICTED, isEntityEditable: IS_ENTITY_EDITABLE
      }),
      deviceDiscovery () {
        return this.dashboard.dataDiscovery.devices.data
      },
      seenDevices () {
        return (this.deviceDiscovery && this.deviceDiscovery.seen)
      },
      isEmptySystem () {
        if (this.deviceDiscovery.seen === undefined || this.dashboardFirstUse === null) return null

        return (!this.seenDevices && this.dashboardFirstUse)
      },
    },
    created () {
      this.fetchDashboardFirstUse()
      const getDashboardData = () => {
        return Promise.all([
          this.fetchDiscoveryData({ module: 'devices' }), this.fetchDiscoveryData({ module: 'users' }),
          this.fetchDashboard()
        ]).then(() => {
          if (this._isDestroyed) return
          this.timer = setTimeout(getDashboardData, 30000)
        })
      }
      getDashboardData().then(() => {
        if (this._isDestroyed || this.isExpired) return
        if (!this.isEmptySystem) this.nextState('dashboard')
        let module = 'devices'
        if (this.isEntityRestricted(module)) return
        this.fetchViews({ module, type: 'saved' }).then(() => {
          if (this.devicesViewsList.length && this.devicesViewsList.find((item) => item.name.includes('DEMO'))) return
          // If DEMO view was not yet added, add it now, according to the adapters' devices count
          if (this.seenDevices && this.isEntityEditable(module)) {
            let adapter = this.deviceDiscovery.counters.find((item) => !item.name.includes('active_directory'))
            let name = ''
            let filter = ''
            if (adapter) {
              // Found an adapters other than Active Directory - view will filter it
              name = adapter.name.split('_').join(' ')
              filter = `adapters == '${adapter.name}'`
            } else {
              // Active Directory is the only adapters - view will filter for Windows 10
              name = 'Windows 10'
              filter = 'specific_data.data.os.distribution == "10"'
            }
            this.saveView({
              name: `DEMO - ${name}`, module: 'devices', predefined: true, view: {
                ...this.devicesView, query: { filter }
              }
            })
          }
        })
      })
    },
    beforeDestroy () {
      clearTimeout(this.timer)
    },
    methods: {
      ...mapMutations({
        changeState: CHANGE_TOUR_STATE, nextState: NEXT_TOUR_STATE
      }),
      ...mapActions({
        fetchDiscoveryData: FETCH_DISCOVERY_DATA,
        fetchDashboardFirstUse: FETCH_DASHBOARD_FIRST_USE,
        fetchDashboard: FETCH_DASHBOARD_SPACES,
        fetchViews: FETCH_DATA_VIEWS, saveView: SAVE_VIEW
      }),
      onClickInsights () {
        this.$router.push({ name: 'Insights Explorer' })
      }
    }
  }
</script>


<style lang="scss">

</style>
