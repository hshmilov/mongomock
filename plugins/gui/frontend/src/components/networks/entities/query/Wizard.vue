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
        @change="onChangeFilter"
        @error="$emit('error')"
      />
      <md-switch
        v-model="isUniqueAdapters"
        :disabled="!value"
        v-if="module == 'devices'"
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
  import xFilter from '../../../neurons/schema/Filter.vue'

  const INCLUDE_OUDATED_MAGIC = 'INCLUDE OUTDATED: '

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
          return this.query.expressions
        },
        set (expressions) {
          this.updateView({
            module: this.module,
            view: {
              query: { filter: this.query.filter, expressions },
              page: 0
            },
            uuid: this.query.filter ? undefined : null
          })
        }
      },
      isUniqueAdapters: {
        get () {
          return this.value.includes(INCLUDE_OUDATED_MAGIC)
        },
        set (isUniqueAdapters) {
          this.sendFilter(isUniqueAdapters ? `${INCLUDE_OUDATED_MAGIC}${this.value}`
            : this.value.replace(INCLUDE_OUDATED_MAGIC, ''))
        }
      },
      prettyModule () {
        return this.module[0].toUpperCase() + this.module.slice(1)
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      compileFilter () {
        // Instruct the filter to re-compile, in case filter was edited
        this.$refs.filter.compile()
        this.$refs.wizard.close()
      },
      clearFilter () {
        // Restart the expressions, search input and filter
        this.queryExpressions = []
        this.isUniqueAdapters = false
        this.$nextTick(() => {
          this.$refs.filter.addExpression()
          this.onChangeFilter('')
        })
      },
      onChangeFilter (filter) {
        if (this.isUniqueAdapters) {
          this.sendFilter(`${INCLUDE_OUDATED_MAGIC}${filter}`)
        } else {
          this.sendFilter(filter)
        }
      },
      sendFilter (filter) {
        this.$emit('input', filter)
      }
    }
  }
</script>

<style lang="scss">
    .x-query-wizard {
        .content {
            padding: 12px;
        }
    }
</style>