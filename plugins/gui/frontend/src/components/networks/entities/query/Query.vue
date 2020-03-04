<template>
  <div class="x-query">
    <x-query-state
      :module="module"
      :valid="filterValid"
      :read-only="readOnly"
      :default-fields="defaultFields"
      @done="$emit('done')"
    />
    <div class="filter">
      <x-query-search-input
        v-model="queryFilter"
        :module="module"
        :query-search.sync="query.search"
        @validate="onValid"
      />
      <x-button
        link
        @click="navigateSavedQueries"
      >Saved Queries</x-button>
      <x-query-wizard
        v-model="query"
        :module="module"
        :error="error"
        @error="onError"
        @submit="() => updateQuery(query, true)"
        @reset="onReset"
      />
    </div>
  </div>
</template>

<script>
import { mapState, mapGetters, mapMutations } from 'vuex';
import xQueryState from './State.vue';
import xQuerySearchInput from './SearchInput.vue';
import xQueryWizard from './Wizard.vue';
import xButton from '../../../axons/inputs/Button.vue';

import { AUTO_QUERY, GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL } from '../../../../store/getters';
import { UPDATE_DATA_VIEW } from '../../../../store/mutations';
import QueryBuilder from '../../../../logic/query_builder';

export default {
  name: 'XQuery',
  components: {
    xQueryState, xQuerySearchInput, xQueryWizard, xButton,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    defaultFields: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      filterValid: true,
      error: '',
    };
  },
  computed: {
    ...mapState({
      view(state) {
        return state[this.module].view;
      },
    }),
    ...mapGetters({
       autoQuery: AUTO_QUERY, getModuleSchemaWithConnectionLabel: GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL,
    }),
    query: {
      get() {
        return this.view.query;
      },
      set(query) {
        this.updateQuery(query, false);
      },
    },
    enforcementFilter() {
      if (!this.view.enforcement) return '';
      return this.view.enforcement.filter;
    },
    queryFilter: {
      get() {
        return this.query.filter;
      },
      set(filter) {
        const prevFilter = this.query.filter;
        const queryMeta = {
          ...this.query.meta,
          enforcementFilter: this.enforcementFilter,
        };
        this.updateView({
          module: this.module,
          view: {
            query: {
              filter,
              expressions: this.query.expressions,
              meta: queryMeta,
              search: this.query.search ? this.query.search : null,
            },
            page: 0,
          },
        });
        this.filterValid = filter !== '';
        if (prevFilter !== filter) {
          this.$emit('done');
        }
      },
    },
    schema() {
      return this.getModuleSchemaWithConnectionLabel(this.module);
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    navigateSavedQueries() {
      this.$router.push({ path: `/${this.module}/query/saved` });
    },
    onValid() {
      this.filterValid = true;
      this.$emit('done');
    },
    onError(error) {
      this.filterValid = false;
      this.error = error;
    },
    compileFilter(query, filter, queryMeta) {
      let resultFilters = {};
      if (query.expressions.length === 0) {
        resultFilters.resultFilter = '';
      } else {
        try {
          const queryBuilder = QueryBuilder(this.schema, query.expressions, queryMeta, query.onlyExpressionsFilter);
          resultFilters = queryBuilder.compileQuery();
          this.error = queryBuilder.getError();
          this.filterValid = !this.error;
        } catch (error) {
          this.onError(error);
          this.filterValid = false;
        }
      }
      return resultFilters;
    },
    updateQuery(query, force = false) {
      const prevFilter = this.query.filter;

      const queryMeta = {
        ...this.query.meta,
        ...query.meta,
        enforcementFilter: this.enforcementFilter,
      };

      const filterShouldRecompile = force || this.autoQuery;
      let filter;
      // Check if the calculation is forced (using the search button) or the autoQuery value is chosen
      let resultFilters = {};
      if (filterShouldRecompile) {
        resultFilters = this.compileFilter(query, filter, queryMeta);
        filter = resultFilters.resultFilter;
      }

      let selectIds = [];
      if (queryMeta && queryMeta.filterOutExpression && queryMeta.filterOutExpression.showIds) {
        selectIds = queryMeta.filterOutExpression.value.split(',');
        queryMeta.filterOutExpression = null;
      }

      // Update the view in any case, even if the filter has not changed
      this.updateView({
        module: this.module,
        view: {
          query: {
            filter: filter || prevFilter,
            onlyExpressionsFilter: filterShouldRecompile ? resultFilters.onlyExpressionsFilter : this.query.onlyExpressionsFilter,
            expressions: query.expressions,
            meta: queryMeta,
            search: null,
          },
          page: 0,
        },
      });

      // Fetch the entities only if the filter has changed
      if (prevFilter !== filter && filter) {
        this.$emit('done', true, selectIds);
      }
    },
    onReset() {
      this.updateView({
        module: this.module,
        view: {
          query: {
            filter: '',
            onlyExpressionsFilter: '',
            meta: {
              uniqueAdapters: false,
              enforcementFilter: this.enforcementFilter,
            },
            expressions: [],
            search: null,
          },
        },
        uuid: null,
      });
      this.$emit('done');
    },
  },
};
</script>

<style lang="scss">
    .x-query {

        > .filter {
          display: flex;

          > .x-button {
            width: 120px;
          }
        }

    }
</style>
