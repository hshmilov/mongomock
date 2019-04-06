<template>
  <div class="x-entity-table">
    <span class="table-results-title"
    >
      <template v-if="ecFilter">
        <i class="text">{{ecResultsMessage}}</i>
        <x-button
          link
          @click="clearEc"
        >Clear</x-button>
        <x-button
          link
          @click="navigateFilteredTask"
        >Go to Task</x-button>
      </template>
      <x-historical-date
        v-model="historical"
        :module="module"
        @error="$emit('error', $event)"
      />
    </span>
    <x-query
      :module="module"
      :read-only="isReadOnly"
    />
    <x-table
      ref="table"
      v-model="isReadOnly? undefined: selection"
      :module="module"
      id-field="internal_axon_id"
      @click-row="configEntity"
      @data="onTableData"
    >
      <template slot="actions">
        <x-action-menu
          v-show="hasSelection"
          :module="module"
          :entities="selection"
          @done="updateEntities"
        />
        <!-- Modal for selecting fields to be presented in table, including adapters hierarchy -->
        <x-field-config :module="module" />
        <x-button
          link
          @click="exportCSV"
        >Export CSV</x-button>
        <x-button
          link
          @click="navigateSavedQueries"
        >Saved Queries</x-button>
      </template>
    </x-table>
  </div>
</template>

<script>
  import xHistoricalDate from '../../neurons/inputs/HistoricalDate.vue'
  import xQuery from '../../neurons/data/Query.vue'
  import xTable from '../../neurons/data/Table.vue'
  import xActionMenu from './ActionMenu.vue'
  import xFieldConfig from './FieldConfig.vue'
  import xButton from '../../axons/inputs/Button.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../../store/mutations'
  import { FETCH_DATA_CONTENT_CSV, FETCH_DATA_FIELDS } from '../../../store/actions'

  export default {
    name: 'XEntityTable',
    components: { xHistoricalDate, xQuery, xTable, xActionMenu, xFieldConfig, xButton },
    props: { module: { required: true } },
    computed: {
      ...mapState({
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions[this.module.charAt(0).toUpperCase() + this.module.slice(1)] === 'ReadOnly'
        },
        historicalState (state) {
          return state[this.module].view.historical
        },
        allowedDates (state) {
          return state.constants.allowedDates[this.module]
        },
        query (state) {
          return state[this.module].view.query
        },
        ecFilter (state) {
          return state[this.module].view.ecFilter
        }
      }),
      historical: {
        get () {
          if (!this.historicalState) return ''
          return this.historicalState.substring(0, 10)
        },
        set (newDate) {
          this.updateView({
            module: this.module, view: {
              historical: this.allowedDates[newDate]
            }
          })
        }
      },
      hasSelection () {
        return (this.selection.ids && this.selection.ids.length) || this.selection.include === false
      },
      ecResultsMessage() {
        return `Showing ${this.ecFilter.success.split('_')[0]} results of action ${this.ecFilter.details.action} of enforcement ${this.ecFilter.details.enforcement}, Task ${this.ecFilter.pretty_id}`
      }
    },
    data () {
      return {
        selection: { ids: [] }
      }
    },
    mounted() {
      this.fetchDataFields({ module: this.module })
    },
    methods: {
      ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
      ...mapActions({
        fetchContentCSV: FETCH_DATA_CONTENT_CSV, fetchDataFields: FETCH_DATA_FIELDS
      }),
      configEntity (entityId) {
        if (this.hasSelection) return

        let path = `${this.module}/${entityId}`
        if (this.historicalState) {
          path += `?history=${encodeURIComponent(this.historicalState)}`
        }
        this.$router.push({ path: path })
      },
      updateEntities () {
        this.$refs.table.fetchContentPages(true)
        this.fetchDataFields({ module: this.module })
        this.selection = { ids: [] }
      },
      exportCSV () {
        this.fetchContentCSV({ module: this.module })
      },
      navigateSavedQueries () {
        this.$router.push({ path: `/${this.module}/query/saved` })
      },
      clearEc () {
        this.updateView({
          module: this.module, view: {
            ecFilter: null,
            query: { ...this.query }
          }
        })
      },
      navigateFilteredTask() {
        this.$router.push({path: `/enforcements/tasks/${this.ecFilter.details.id}`})
      },
      onTableData (dataId) {
        this.$emit('data', dataId)
      }
    }
  }
</script>

<style lang="scss">
    .x-entity-table {
        height: calc(100% - 36px);
    }
    .table-results-title {
        display: flex;
        align-items: center;
        .x-historical-date {
            flex: 1 0 auto;
        }

    }
</style>