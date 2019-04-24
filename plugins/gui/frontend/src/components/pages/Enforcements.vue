<template>
  <x-page
    title="Enforcement Center"
    class="x-enforcements"
    :class="{disabled: isReadOnly}"
  >
    <x-search
      v-model="searchValue"
      placeholder="Search Enforcement Sets..."
      @keyup.enter.native="onSearchConfirm"
    />
    <x-table
      v-model="isReadOnly? undefined: selection"
      module="enforcements"
      title="Enforcement Sets"
      :static-fields="fields"
      @click-row="navigateEnforcement"
    >
      <template slot="actions">
        <x-button
          v-if="hasSelection"
          link
          @click="remove"
        >Remove</x-button>
        <x-button
          id="enforcement_new"
          :disabled="isReadOnly"
          @click="navigateEnforcement('new')"
        >+ New Enforcement</x-button>
        <x-button
          emphasize
          @click="navigateTasks"
        >View Tasks</x-button>
      </template>
    </x-table>
  </x-page>
</template>


<script>
  import xPage from '../axons/layout/Page.vue'
  import xSearch from '../neurons/inputs/SearchInput.vue'
  import xTable from '../neurons/data/Table.vue'
  import xButton from '../axons/inputs/Button.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../store/mutations'
  import { REMOVE_ENFORCEMENTS, FETCH_ENFORCEMENT } from '../../store/modules/enforcements'
  import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

  export default {
    name: 'XEnforcements',
    components: {
      xPage, xSearch, xTable, xButton
    },
    data () {
      return {
        selection: { ids: [] },
        searchValue: ''
      }
    },
    computed: {
      ...mapState({
        tourEnforcements (state) {
          return state.onboarding.tourStates.queues.enforcements
        },
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Enforcements === 'ReadOnly'
        }
      }),
      name () {
        return 'enforcements'
      },
      fields () {
        return [{
          name: 'name', title: 'Name', type: 'string'
        }, {
          name: 'last_updated', title: 'Last Updated', type: 'string', format: 'date-time'
        }, {
          name: 'actions.main', title: 'Main Action', type: 'string'
        }, {
          name: 'triggers.view.name', title: 'Trigger Query Name', type: 'string'
        }, {
          name: 'triggers.last_triggered', title: 'Last Triggered', type: 'string', format: 'date-time'
        }, {
          name: 'triggers.times_triggered', title: 'Times Triggered', type: 'integer'
        }]
      },
      hasSelection () {
        return (this.selection.ids && this.selection.ids.length) || this.selection.include === false
      },
      searchFilter() {
        let patternParts = []
        this.fields.forEach((field) => {
          patternParts.push(field.name + ` == regex("${this.searchValue}", "i")`)
        })
        return patternParts.join(' or ')
      }
    },
    created () {
      if (this.tourEnforcements && this.tourEnforcements.length) {
        this.changeState({ name: this.tourEnforcements[0] })
      }
    },
    methods: {
      ...mapMutations({ updateView: UPDATE_DATA_VIEW, changeState: CHANGE_TOUR_STATE }),
      ...mapActions({
        removeEnforcements: REMOVE_ENFORCEMENTS, fetchEnforcement: FETCH_ENFORCEMENT
      }),
      navigateEnforcement (enforcementId) {
        this.fetchEnforcement(enforcementId)
        this.$router.push({ path: `/${this.name}/${enforcementId}` })
      },
      remove () {
        this.removeEnforcements(this.selection)
        this.selection = { ids: [] }
      },
      navigateTasks () {
        this.updateView({
          module: 'tasks',
          view: {
            query: {
              filter: ''
            }
          }
        })
        this.$router.push({ name: 'Tasks' })
      },
      onSearchConfirm() {
        this.updateView({
          module: this.name,
          view: {
            query: {
              filter: this.searchFilter
            },
            page: 0
          }
        })
      }
    }
  }
</script>


<style lang="scss">
    .x-enforcements {
        .x-button {
            width: auto;
        }
    }
</style>