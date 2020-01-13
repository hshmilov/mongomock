<template>
  <x-dropdown
    ref="wizard"
    class="x-query-wizard"
    align="right"
    :align-space="4"
    :align-agile="false"
    size="xl"
    :arrow="false"
    @activated="$emit('activated')"
  >
    <x-button
      id="query_wizard"
      slot="trigger"
    >+ Query Wizard</x-button>
    <div slot="content">
      <x-filter
        ref="filter"
        v-model="queryExpressions"
        :module="module"
        :error="error"
        @change="onChangeFilter"
        @clear="clearFilter"
        @error="onError"
      />
      <div
        v-if="!filterOutExpression.showIds && filterOutIdCount > 0"
        class="filter-out-ids"
      >Filtered out from query results ({{ filterOutIdCount }})
        <x-button
          key="remove-filter-out"
          link
          class="remove-filter-out"
          @click="removeFilterOutExpression"
        >Clear</x-button>
      </div>
      <md-switch
        v-model="isUniqueAdapters"
        :disabled="!value"
        v-if="module === 'devices'"
      >Include outdated Adapter {{ prettyModule }}
        in query
      </md-switch>
      <div class="place-right">
        <x-button
          link
          @click="clearFilter"
          @keyup.enter.native="clearFilter"
        >Clear</x-button>
        <x-button
          @click="compileFilter"
          @keyup.enter.native="compileFilter"
        >Search</x-button>
      </div>
    </div>
  </x-dropdown>
</template>

<script>
  import xDropdown from '../../../axons/popover/Dropdown.vue'
  import xButton from '../../../axons/inputs/Button.vue'
  import xFilter from '../../../neurons/schema/query/Filter.vue'

  import { mapState, mapMutations } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../../../store/mutations'

  export default {
    name: 'XQueryWizard',
    components: {
      xDropdown, xButton, xFilter
    },
    props: {
      module: {
        type: String,
        required: true
      },
      value: {
        type: Object,
        default: () => {}
      },
      error: {
          type: String,
          default: ''
      }
    },
    computed: {
      ...mapState({
        query (state) {
          return state[this.module].view.query
        }
      }),
      queryExpressions: {
        get () {
          return this.value.expressions
        },
        set (expressions) {
          this.updateQuery(this.value.filter, this.value.onlyExpressionsFilter, this.value.meta, expressions)
        }
      },
      isUniqueAdapters: {
        get () {
          return this.value.meta ? this.value.meta.uniqueAdapters : false
        },
        set (isUniqueAdapters) {
          const meta = {...this.value.meta, uniqueAdapters: isUniqueAdapters}
          this.updateQuery(this.value.filter, this.value.onlyExpressionsFilter, meta, this.value.expressions)
        }
      },
      prettyModule () {
        return this.module[0].toUpperCase() + this.module.slice(1)
      },
      filterOutExpression() {
        return this.value.meta && this.value.meta.filterOutExpression ? this.value.meta.filterOutExpression : {}
      },
      filterOutIdCount() {
        return this.value.meta && this.value.meta.filterOutExpression ? this.value.meta.filterOutExpression.value.split(',').length : 0
      },
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      compileFilter () {
        // Instruct the filter to re-compile, in case filter was edited
        this.$emit('submit')
        this.$refs.wizard.close()
      },
      clearFilter () {
        this.$emit('reset')
         this.$nextTick(() => {
             this.$refs.filter.reset()
         })
      },
      onChangeFilter (expressions) {
        this.updateQuery(this.value.filter, this.value.onlyExpressionsFilter, this.value.meta, expressions)
      },
      onError(error){
          this.$emit('error', error)
      },
      removeFilterOutExpression(){
        const filterOutExpression = {...this.value.meta.filterOutExpression}
        filterOutExpression.showIds = true
        const meta = {...this.value.meta, filterOutExpression: filterOutExpression}
        this.updateQuery(this.value.filter, this.value.onlyExpressionsFilter, meta, this.value.expressions)
        this.$refs.wizard.close()
      },
      updateQuery(filter, onlyExpressionsFilter, meta, expressions){
        this.$emit('input', {
          filter: filter,
          onlyExpressionsFilter: onlyExpressionsFilter,
          meta: meta,
          expressions: expressions
        })
      }
    }
  }
</script>

<style lang="scss">
    .x-query-wizard {
        .content {
            padding: 12px;

          .filter-out-ids {
            display: block;
            padding-top: 16px;
            .link {
              padding-left: 4px;
            }
          }
        }
    }
</style>
