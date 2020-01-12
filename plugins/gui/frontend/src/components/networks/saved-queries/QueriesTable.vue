<template>
  <div class="x-queries-table">
    <section class="queries-table-header">
      <div class="queries-table-header__search">
        <x-search
          v-model="searchValue"
          class="search__input"
          placeholder="Search Queries..."
          @keyup.enter.native="updateCurrentView"
        />
        <x-button 
          class="search__reset" 
          link 
          @click="resetSearchAndFilters"
        >Reset</x-button>
      </div>
      <x-button 
        link 
        @click="openAxoniusDocs"
      >
        <v-icon 
          small
          color="secondary"
        >{{ helpIconSvgPath }}</v-icon>Learn about Axonius use cases
      </x-button>
    </section>
    <x-saved-queries-panel
      v-model="isPanelOpen" 
      :namespace="module" 
      @input="panelStateChanged" 
      @run="runQuery" 
      @delete="handleSelectedQueriesDeletion" 
      @save-changes="saveQueryChanges" 
      @close="closeQuerySidePanel" 
      @new-enforcement="createEnforcement"
    />
    <x-table
      ref="table"
      v-model="queriesRowsSelections"
      :module="pathToSavedQueryInState"
      title="Saved Queries"
      :static-fields="queriesTableFieldsSchema"
      :on-click-row="openQuerySidePanel"
    >
      <template slot="actions">
        <x-button 
          v-if="hasSelection"  
          id="remove-queries-btn" 
          :disabled="readOnly" 
          link 
          @click="handleSelectedQueriesDeletion"
        >Remove</x-button>
      </template>
    </x-table>
  </div>
</template>

<script>
  import xSearch from '../../neurons/inputs/SearchInput.vue'
  import xTable from '../../neurons/data/Table.vue'
  import xButton from '../../axons/inputs/Button.vue'
  import xSavedQueriesPanel from './SavedQueryPanel'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../../store/mutations'
  import { DELETE_DATA, SAVE_VIEW } from '../../../store/actions'
  import { SET_ENFORCEMENT, initTrigger } from '../../../store/modules/enforcements'

  import { mdiHelpCircleOutline } from '@mdi/js'
  import _get from 'lodash/get'

  export default {
    name: 'XQueriesTable',
    components: {
      xSearch, xTable, xButton, xSavedQueriesPanel
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
        isPanelOpen: false,
        selection: { ids: [], include: true },
        searchValue: '',
        helpIconSvgPath: mdiHelpCircleOutline,
      }
    },
    computed: {
      ...mapState({
        savedQueries (state) {
          return state[this.module].views.saved.content.data
        },
        isEnforcementsWrite (state) {
          const user = _get(state, 'auth.currentUser.data')
          const noUserOrPermissionsDefined = !user || !user.permissions
          const userEnforcementsPermissionsLevel = _get(user, permissions.Enforcements)
          const isUserAdminRole = user.admin

          return userEnforcementsPermissionsLevel === 'ReadWrite' || noUserOrPermissionsDefined || isUserAdminRole
        }
      }),
      queriesRowsSelections: {
        get() {
          return this.readOnly ? undefined : this.selection
        },
        set(newSelections) {
          this.selection = newSelections
        }
      },
      pathToSavedQueryInState() {
        return `${this.module}/views/saved`
      },
      hasSelection () {
        return (this.selection.ids && this.selection.ids.length) || this.selection.include === false
      },
      numberOfSelections() {
        return this.selection.ids ? this.selection.ids.length : 0
      },
      queriesTableFieldsSchema() {
        return [
          {
            name: 'name', 
            title: 'Name', 
            type: 'string',
          },
          {
            name: 'description', 
            title: 'Description', 
            type: 'string',
          },
          {
            name: 'tags', 
            title: 'Tags', 
            type: 'array', 
            items: {
              format: 'tag',
              type: 'string'
            }
          },
          {
            name: 'last_updated', title: 'Last Updated', type: 'string', format: 'date-time'
          },
          {
            name: 'updated_by', title: 'Updated By', type: 'string'
          },
        ]
      },
      searchFilter() {
        if (!this.searchValue) return ''
        return `name == regex("${this.searchValue}", "i") or description == regex("${this.searchValue}", "i")`
      },
      selectedName () {
        return this.savedQueries.filter(v => v).find(view => this.selection.ids[0] === view.uuid).name
      }
    },
    mounted(){
      const { queryId } = this.$route.params
      if (queryId) {
        this.isPanelOpen = true
        this.selection.ids = [queryId]
      }
    },
    methods: {
      async saveQueryChanges({queryData, done}) {
        try {
          await this.updateQuery({
            module: this.module,
            ...queryData
          })
          done()
        } catch (ex) {
          done(ex)
        }
      },
      runQuery (viewId) {
        const selectedView = this.savedQueries.find(view => view.uuid === viewId)
        this.updateView({
          module: this.module,
          view: selectedView.view,
          uuid: selectedView.uuid
        })
        this.$router.push({ path: `/${this.module}` })
      },
      createEnforcement (queryName) {
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
              name: queryName, entity: this.module
            }
          }]
        })
        /* Navigating to new enforcement - requested queries will be selected as triggers there */
        this.$router.push({ path: '/enforcements/new' })
      },
      async handleSelectedQueriesDeletion(e, queryId) {
        if (queryId) {
          // The remover invoked from within the panel and the panel should be closed.
          this.closeQuerySidePanel()
        }
        this.$safeguard.show({
          text: `
            The selected Saved ${ this.numberOfSelections > 1 ? 'Queries' : 'Query' } will be completely removed from the
            system and no other user will be able to use it.
            <br />
            Removing the Saved ${ this.numberOfSelections > 1 ? 'Queries' : 'Query' } is an irreversible action.
            <br />Do you wish to continue?
          `,
          confirmText: this.numberOfSelections > 1 ? 'Remove Saved Queries' : 'Remove Saved Query',
          onConfirm: async () => {
            try {
              await this.removeData({ module: this.pathToSavedQueryInState, selection: !queryId ? this.selection : {ids: [queryId], include: true} })
              this.updateCurrentView()
              this.closeQuerySidePanel()
            } catch(ex) {
              console.error(ex)
            }
          }
        })
      },
      panelStateChanged(open) {
        if(!open) {
          this.$router.push({ name: `${this.module}-queries`})
          this.resetTableSelections()
        }
      },  
      openQuerySidePanel(selectedQueryId) {
        this.isPanelOpen = !this.isPanelOpen
        this.selection = { ids: [selectedQueryId], include: true }
        this.$router.push({ path: '', params: { queryId: selectedQueryId } })
      },
      closeQuerySidePanel() {
        this.isPanelOpen = false
      },
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW, setEnforcement: SET_ENFORCEMENT
      }),
      ...mapActions({
        removeData: DELETE_DATA,
        updateQuery: SAVE_VIEW
      }),
      resetSearchAndFilters() {
        this.searchValue = ''
        this.updateCurrentView()
      },
      openAxoniusDocs() {
        window.open('https://docs.axonius.com/docs/use-cases', '_blank')
      },
      resetTableSelections() {
        this.selection.ids = []
      },
      updateCurrentView () {
        this.resetTableSelections()
        this.updateView({
          module: this.pathToSavedQueryInState,
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

    .table-td-name {
      width: 450px;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .table-td-description {
      max-width: 550px;
      text-overflow: ellipsis;
    }
    .table-td-content-description {
      max-width: 100%;
      text-overflow: ellipsis;
      overflow: hidden;
    }
  }

  .queries-table-header {
    display: flex;
    justify-content: space-between;
    .queries-table-header__search {
      width: 30%;
      display: flex;
      .search__input {
        width: 90%;
      }
      .search__reset {
        width: 10%;
      }
    }
  }

</style>