<template>
  <div class="x-queries-table">
    <x-search
      v-model="searchValue"
      placeholder="Search Query Name..."
      @keyup.enter.native="onSearchConfirm"
    />
    <x-table
      ref="table"
      v-model="readOnly? undefined: selection"
      :module="stateLocation"
      title="Saved Queries"
      :static-fields="fields"
      :on-click-row="runQuery"
    >
      <template slot="actions">
        <x-button
          v-if="selection.ids.length === 1"
          :disabled="!isEnforcementsWrite"
          link
          @click="createEnforcement"
        >+ New Enforcement</x-button>
        <x-safeguard-button
          v-if="hasSelection"
          :disabled="readOnly"
          link
          :approve-text="numberOfSelections > 1 ? 'Remove Saved Queries' : 'Remove Saved Query' "
          @click="removeQuery"
        >
          <div slot="button-text">Remove</div>
          <div slot="message">
            The selected Saved {{ numberOfSelections > 1 ? 'Queries' : 'Query' }} will be completely removed from the
            system and no other user will be able to use it.<br>
            Removing the Saved {{ numberOfSelections > 1 ? 'Queries' : 'Query' }} is an irreversible action.<br>
            Do you wish to continue?
          </div>
        </x-safeguard-button>
      </template>
    </x-table>
  </div>
</template>

<script>
  import xSearch from '../../neurons/inputs/SearchInput.vue'
  import xTable from '../../neurons/data/Table.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import xSafeguardButton from '../../axons/inputs/SafeguardButton.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../../store/mutations'
  import { DELETE_DATA } from '../../../store/actions'
  import { SET_ENFORCEMENT, initTrigger } from '../../../store/modules/enforcements'

  export default {
    name: 'XQueriesTable',
    components: {
      xSearch, xTable, xButton, xSafeguardButton
    },
    props: {
      module: {
        type: String,
        required: true
      },
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        selection: { ids: [], include: true },
        searchValue: ''
      }
    },
    computed: {
      ...mapState({
        views (state) {
          return state[this.module].views.saved.content.data
        },
        isEnforcementsWrite (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Enforcements === 'ReadWrite' || user.admin
        }
      }),
      stateLocation() {
        return `${this.module}/views/saved`
      },
      hasSelection () {
        return (this.selection.ids && this.selection.ids.length) || this.selection.include === false
      },
      numberOfSelections() {
        return this.selection.ids ? this.selection.ids.length : 0
      },
      fields() {
        return [{
          name: 'name', title: 'Name', type: 'string'
        }, {
          name: 'last_updated', title: 'Last Updated', type: 'string', format: 'date-time'
        }, {
          name: 'updated_by', title: 'Updated By', type: 'string'
        }]
      },
      searchFilter() {
        if (!this.searchValue) return ''
        return `name == regex("${this.searchValue}", "i")`
      },
      selectedName () {
        return this.views.find(view => this.selection.ids[0] === view.uuid).name
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW, setEnforcement: SET_ENFORCEMENT
      }),
      ...mapActions({
        removeData: DELETE_DATA
      }),
      runQuery (viewId) {
        let selectedView = this.views.find(view => view.uuid === viewId)
        this.updateView({
          module: this.module,
          view: selectedView.view,
          uuid: selectedView.uuid
        })
        this.$router.push({ path: `/${this.module}` })
      },
      createEnforcement () {
        this.setEnforcement({
          uuid: 'new',
          actions: {
            main: null,
            success: [],
            failure: [],
            post: []
          },
          triggers: [{
            ...initTrigger,
            name: 'Trigger',
            view: {
              name: this.selectedName, entity: this.module
            }
          }]
        })
        /* Navigating to new enforcement - requested queries will be selected as triggers there */
        this.$router.push({ path: '/enforcements/new' })
      },
      removeQuery () {
        this.removeData({ module: this.stateLocation, selection: this.selection })
                .then(this.onSearchConfirm)
        this.selection = {
          ids: [], include: true
        }
      },
      onSearchConfirm () {
        this.updateView({
          module: this.stateLocation,
          view: {
            query: {
              filter: this.searchFilter
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
  .x-queries-table {
    height: 100%;
  }

</style>