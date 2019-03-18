<template>
  <div class="x-entity-table">
    <span
      v-if="ecFilter"
      class="ec_results"
      style="float:left"
    >
      <i>Showing results of action {{ ecFilter.details.action }} from enforcement {{ ecFilter.details.enforcement }}</i>
      <x-button
        link
        @click="clearEc"
      >clear</x-button>
    </span>
    <span class="historical">
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
      }
    },
    data () {
      return {
        selection: { ids: [] }
      }
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

    .historical {
        float: right;
    }

    .ec_results {
        float: left;
    }
</style>