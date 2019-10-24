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

  import viewsMixin from '../../mixins/views'

  import {
    FETCH_DISCOVERY_DATA, FETCH_DASHBOARD_SPACES, FETCH_DASHBOARD_PANELS, FETCH_DASHBOARD_FIRST_USE
  } from '../../store/modules/dashboard'
  import { IS_EXPIRED } from '../../store/getters'
  import { SAVE_VIEW } from '../../store/actions'
  import { IS_ENTITY_RESTRICTED, IS_ENTITY_EDITABLE } from '../../store/modules/auth'
  import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'

  export default {
    name: 'XDashboard',
    components: {
      xPage, xEmptySystem, xSearchInsights, xSpaces
    },
    mixins: [viewsMixin],
    computed: {
      ...mapState({
        dashboard (state) {
          return state.dashboard
        },
        spaces (state) {
          let spaceToPanels = {}
          state.dashboard.panels.data.forEach(panel => {
            if (!spaceToPanels[panel.space]) {
              spaceToPanels[panel.space] = []
            }
            spaceToPanels[panel.space].push(panel)
          })
          return state.dashboard.spaces.data.map(space => {
            return { ...space,
              'panels': spaceToPanels[space.uuid] || []
            }
          })
        },
        devicesView (state) {
          return state.devices.view
        },
        devicesViewsList (state) {
          return state.devices.views.saved.content.data
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
      if (this.isExpired) {
        this.getDashboardData()
      }
    },
    beforeDestroy () {
      clearTimeout(this.timer)
    },
    methods: {
      ...mapActions({
        fetchDiscoveryData: FETCH_DISCOVERY_DATA,
        fetchDashboardFirstUse: FETCH_DASHBOARD_FIRST_USE,
        fetchSpaces: FETCH_DASHBOARD_SPACES, fetchPanels: FETCH_DASHBOARD_PANELS,
        saveView: SAVE_VIEW
      }),
      onClickInsights () {
        this.$router.push({ name: 'Insights Explorer' })
      },
      getDashboardData () {
        return Promise.all([
          this.fetchDiscoveryData({ module: 'devices' }), this.fetchDiscoveryData({ module: 'users' }),
          this.fetchSpaces()
        ]).then(this.fetchPanels).then(() => {
          if (this._isDestroyed) return
          this.timer = setTimeout(this.getDashboardData, 30000)
        })
      },
      viewsCallback () {
        this.getDashboardData()
      }
    }
  }
</script>


<style lang="scss">

</style>
