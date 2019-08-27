<template>
  <div class="x-queries-table">
    <x-search
      v-model="searchValue"
      placeholder="Search Query Name..."
      @keyup.enter.native="onSearchConfirm"
    />
    <x-table
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
        <x-button
          v-if="hasSelection"
          :disabled="readOnly"
          link
          @click="removeQuery"
        >Remove</x-button>
      </template>
    </x-table>
  </div>
</template>

<script>
  import xSearch from '../../neurons/inputs/SearchInput.vue'
  import xTable from '../../neurons/data/Table.vue'
  import xButton from '../../axons/inputs/Button.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../../store/mutations'
  import { DELETE_DATA } from '../../../store/actions'
  import { SET_ENFORCEMENT, initTrigger } from '../../../store/modules/enforcements'

  export default {
    name: 'XQueriesTable',
    components: {
      xSearch, xTable, xButton
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
      fields() {
        return [{
          name: 'name', title: 'Name', type: 'string'
        }, {
          name: 'timestamp', title: 'Last Updated', type: 'string', format: 'date-time'
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
      }
    }
  }
</script>

<style lang="scss">
  .x-queries-table {
    height: 100%;
  }

</style>