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
      ref="table"
      v-model="isReadOnly? undefined: selection"
      module="enforcements"
      title="Enforcement Sets"
      :static-fields="fields"
      :on-click-row="navigateEnforcement"
    >
      <template slot="actions">
        <x-safeguard-button
          v-if="hasSelection"
          link
          :approve-text="numberOfSelections > 1 ? 'Remove Enforcement Sets' : 'Remove Enforcement Set' "
          @click="remove"
        >
          <div slot="button-text">Remove</div>
          <div slot="message">
            The selected Enforcement {{ numberOfSelections > 1 ? 'Sets' : 'Set' }} will be completely removed from the system.<br>
            Removing the Enforcement {{ numberOfSelections > 1 ? 'Sets' : 'Set' }} is an irreversible action.<br>
            Do you wish to continue?
          </div>
        </x-safeguard-button>
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
  import xSafeguardButton from '../axons/inputs/SafeguardButton.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../store/mutations'
  import { REMOVE_ENFORCEMENTS, FETCH_ENFORCEMENT } from '../../store/modules/enforcements'

  export default {
    name: 'XEnforcements',
    components: {
      xPage, xSearch, xTable, xButton, xSafeguardButton
    },
    data () {
      return {
        selection: { ids: [], include: true },
        searchValue: ''
      }
    },
    computed: {
      ...mapState({
        query (state) {
          return state.enforcements.view.query
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
      numberOfSelections() {
        return this.selection.ids ? this.selection.ids.length : 0
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
      if (this.query) {
        this.searchValue = this.query.search
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      ...mapActions({
        removeEnforcements: REMOVE_ENFORCEMENTS, fetchEnforcement: FETCH_ENFORCEMENT
      }),
      navigateEnforcement (enforcementId) {
        this.fetchEnforcement(enforcementId)
        this.$router.push({ path: `/${this.name}/${enforcementId}` })
      },
      remove () {
        this.removeEnforcements(this.selection)
        this.selection = { ids: [], include: true }
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
              filter: this.searchFilter,
              search: this.searchValue
            },
            page: 0
          }
        })
        this.$refs.table.fetchContentPages(true)
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