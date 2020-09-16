<template>
  <XDropdown
    ref="wizard"
    class="x-query-wizard"
    align="right"
    :align-space="4"
    :align-agile="false"
    size="xl"
    :arrow="false"
    @activated="$emit('activated')"
    :no-border-radius="true"
  >
    <XButton
      id="query_wizard"
      slot="trigger"
      type="primary"
    >Query Wizard</XButton>
    <template #content>
      <XFilter
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
        <XButton
          key="remove-filter-out"
          type="link"
          class="remove-filter-out"
          @click="removeFilterOutExpression"
        >Clear</XButton>
      </div>
      <MdSwitch
        v-if="module === 'not_entities'"
        v-model="isUniqueAdapters"
        :disabled="!value.filter"
      >Include outdated Adapter {{ prettyModule }} in query</MdSwitch>
      <div class="place-right">
        <XButton
          type="link"
          @click="clearFilter"
          @keyup.enter.native="clearFilter"
        >Clear</XButton>
        <XButton
          type="primary"
          :disabled="searchDisabled"
          @click="compileFilter"
          @keyup.enter.native="compileFilter"
        >Search</XButton>
      </div>
    </template>
  </XDropdown>
</template>

<script>
import { mapState } from 'vuex';
import _debounce from 'lodash/debounce';
import _isEmpty from 'lodash/isEmpty';

import XDropdown from '../../../axons/popover/Dropdown.vue';
import XButton from '../../../axons/inputs/Button.vue';
import XFilter from '../../../neurons/schema/query/Filter.vue';

export default {
  name: 'XQueryWizard',
  components: {
    XDropdown, XButton, XFilter,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    value: {
      type: Object,
      default: () => {},
    },
    error: {
      type: String,
      default: '',
    },
  },
  computed: {
    ...mapState({
      query(state) {
        return state[this.module].view.query;
      },
    }),
    queryExpressions: {
      get() {
        return this.value.expressions;
      },
      set(expressions) {
        this.debouncedUpdateQueryEvent(this.value.filter, this.value.onlyExpressionsFilter, this.value.meta, expressions);
      },
    },
    isUniqueAdapters: {
      get() {
        return this.value.meta ? this.value.meta.uniqueAdapters : false;
      },
      set(isUniqueAdapters) {
        const meta = { ...this.value.meta, uniqueAdapters: isUniqueAdapters };
        this.updateQuery(this.value.filter, this.value.onlyExpressionsFilter, meta, this.value.expressions);
      },
    },
    prettyModule() {
      return this.module[0].toUpperCase() + this.module.slice(1);
    },
    filterOutExpression() {
      return this.value.meta && this.value.meta.filterOutExpression ? this.value.meta.filterOutExpression : {};
    },
    filterOutIdCount() {
      return this.value.meta && this.value.meta.filterOutExpression ? this.value.meta.filterOutExpression.value.split(',').length : 0;
    },
    searchDisabled() {
      return !_isEmpty(this.error);
    },
  },
  methods: {
    compileFilter() {
      // Instruct the filter to re-compile, in case filter was edited
      this.$emit('submit');
      this.$refs.wizard.close();
    },
    clearFilter() {
      this.$emit('reset');
      this.$nextTick(() => {
        this.$refs.filter.reset();
      });
      this.$refs.wizard.clearStyles();
    },
    onChangeFilter(expressions) {
      this.debouncedUpdateQueryEvent(this.value.filter, this.value.onlyExpressionsFilter, this.value.meta, expressions);
    },
    onError(error) {
      this.$emit('error', error);
    },
    removeFilterOutExpression() {
      const filterOutExpression = { ...this.value.meta.filterOutExpression };
      filterOutExpression.showIds = true;
      const meta = { ...this.value.meta, filterOutExpression };
      this.debouncedUpdateQueryEvent(this.value.filter, this.value.onlyExpressionsFilter, meta, this.value.expressions);
      this.$refs.wizard.close();
    },
    debouncedUpdateQueryEvent: _debounce(function debouncedUpdateQueryEvent(...args) {
      this.updateQuery(...args);
    }, 400, {
      leading: true,
      trailing: true,
    }),
    updateQuery(filter, onlyExpressionsFilter, meta, expressions) {
      this.$emit('input', {
        filter,
        onlyExpressionsFilter,
        meta,
        expressions,
      });
    },
  },
};
</script>

<style lang="scss">
  .x-query-wizard {
    .content {
      padding: 12px;

      .x-filter {
        height: calc(100% - 30px);
      }

      .filter-out-ids {
        display: block;
        padding-top: 16px;

        .ant-btn-link {
          padding-left: 4px;
        }
      }
    }
  }
</style>
