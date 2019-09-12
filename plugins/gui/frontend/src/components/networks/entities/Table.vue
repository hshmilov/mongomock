<template>
  <div class="x-entity-table">
    <x-query
      :module="module"
      :read-only="isReadOnly"
      @done="updateEntities"
    />
    <x-table
      ref="table"
      v-model="isReadOnly? undefined: selection"
      :module="module"
      id-field="internal_axon_id"
      :expandable="true"
      :filterable="true"
      :on-click-row="configEntity"
      @input="updateSelection"
      @data="onTableData"
    >
      <template slot="actions">
        <x-action-menu
          v-show="hasSelection"
          :module="module"
          :entities="selection"
          :entities-meta="selectionLabels"
          @done="updateEntities"
        />
        <!-- Modal for selecting fields to be presented in table, including adapters hierarchy -->
        <x-field-config
          :module="module"
          @done="updateEntities"
        />

        <x-button
          v-if="!exporting"
          link
          @click="exportCSV"
        >Export CSV</x-button>
        <div
          v-if="exporting"
          class="loading-button"
        >
          <md-progress-spinner
            class="progress-spinner"
            md-mode="indeterminate"
            :md-stroke="3"
            :md-diameter="30"
          />
          <x-button
            link
            disabled
            class="exporting-loader"
          >Exporting...</x-button>
        </div>
      </template>
      <x-table-data
        slot-scope="props"
        :module="module"
        v-bind="props"
      />
    </x-table>
  </div>
</template>

<script>
  import xQuery from './query/Query.vue'
  import xTable from '../../neurons/data/Table.vue'
  import xTableData from './TableData.vue'
  import xActionMenu from './ActionMenu.vue'
  import xFieldConfig from './FieldConfig.vue'
  import xButton from '../../axons/inputs/Button.vue'

  import { mapState, mapMutations, mapActions } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../../store/mutations'
  import {
    FETCH_DATA_CONTENT_CSV, FETCH_DATA_FIELDS, FETCH_DATA_CURRENT
  } from '../../../store/actions'

  export default {
    name: 'XEntityTable',
    components: {
      xQuery, xTable, xTableData, xActionMenu, xFieldConfig, xButton
    },
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
        currentSelectionLabels (state) {
          if (!this.selection.include) return {}
          return state[this.module].content.data
                  .filter(entity => this.selection.ids.includes(entity.internal_axon_id))
                  .reduce((entityToLabels, entity) => {
                    entityToLabels[entity.internal_axon_id] = entity.labels
                    return entityToLabels
                  }, {})
        }
      }),
      hasSelection () {
        return (this.selection.ids && this.selection.ids.length) || this.selection.include === false
      }
    },
    data () {
      return {
        selection: { ids: [], include: true },
        selectionLabels: {},
        exporting: false
      }
    },
    methods: {
      ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
      ...mapActions({
        fetchContentCSV: FETCH_DATA_CONTENT_CSV, fetchDataFields: FETCH_DATA_FIELDS,
        fetchDataCurrent: FETCH_DATA_CURRENT
      }),
      configEntity (entityId) {
        if (this.hasSelection) return

        let path = `${this.module}/${entityId}`
        if (this.historicalState) {
          path += `?history=${encodeURIComponent(this.historicalState)}`
        }
        this.$router.push({ path: path })
        this.fetchDataCurrent({
          module: this.module,
          id: entityId,
          history: this.historicalState
        })
      },
      updateEntities (reset = true) {
        this.$refs.table.fetchContentPages(true)
        this.fetchDataFields({ module: this.module })
        if (reset) {
          this.selection = {'ids': [], include: true}
        } else {
          this.updateSelection(this.selection)
        }
      },
      exportCSV () {
        this.fetchContentCSV({ module: this.module }).then(() => {
          this.exporting = false
        })
        this.exporting = true

      },
      onTableData (dataId) {
        this.$emit('data', dataId)
      },
      updateSelection (selection) {
        if (!selection.include) {
          this.selectionLabels = {}
        } else {
          this.$nextTick(() => {
            this.selectionLabels = selection.ids.reduce((entityToLabels, entity) => {
              entityToLabels[entity] = this.currentSelectionLabels[entity] || this.selectionLabels[entity] || []
              return entityToLabels
            }, {})
          })
        }
      }
    }
  }
</script>

<style lang="scss">
    .x-entity-table {
        height: 100%;
        .x-table-wrapper .actions {
          grid-gap: 0;
          > .x-button.link {
            width: 120px;
          }
        }

        .md-progress-spinner-circle{
            stroke: #0076FF;
        }

        .table-header {
            .actions {
                .loading-button {
                    width: 120px;
                    .progress-spinner {
                        height: 15px;
                        .md-progress-spinner-draw {
                            width: 15px !important;
                            height: 15px !important;;
                        }
                    }
                    button.exporting-loader.link {
                        padding-left: 8px;
                        width: 80px;
                    }
                }

            }
        }
    }

</style>