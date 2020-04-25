<template>
  <div class="x-query">
    <XQueryState
      :module="module"
      :valid="filterValid"
      :read-only="readOnly"
      :user-fields-groups="userFieldsGroups"
      @done="$emit('done')"
      @reset-search="$refs.searchInput.resetSearchInput()"
    />
    <div class="filter">
      <XQuerySearchInput
        v-model="queryFilter"
        :module="module"
        :query-search.sync="query.search"
        :user-fields-groups="userFieldsGroups"
        @validate="onValid"
        @done="$emit('done')"
        ref="searchInput"
      />
      <XButton
        type="link"
        @click="navigateSavedQueries"
      >Saved Queries</XButton>
      <XQueryWizard
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
import _isEqual from 'lodash/isEqual';
import _cloneDeep from 'lodash/cloneDeep';
import { AUTO_QUERY, GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL } from '@store/getters';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import XButton from '@axons/inputs/Button.vue';
import XQueryState from './State.vue';
import XQuerySearchInput from './SearchInput.vue';
import XQueryWizard from './Wizard.vue';
import QueryBuilder from '../../../../logic/query_builder';

export default {
  name: 'XQuery',
  components: {
    XQueryState, XQuerySearchInput, XQueryWizard, XButton,
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
    userFieldsGroups: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      filterValid: true,
      error: '',
      prevExpressions: {},
      recompiledFilter: '',
    };
  },
  computed: {
    ...mapState({
      view(state) {
        return state[this.module].view;
      },
    }),
    ...mapGetters({
      autoQuery: AUTO_QUERY,
      getModuleSchemaWithConnectionLabel: GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL,
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
  mounted() {
    const { selectedQueryId } = this.$route.query;
    // If we navigated to this page with a new query (selected from the queries page)
    // We need to set the new expression and filter
    if (selectedQueryId) {
      this.prevExpressions = this.query.expressions;
      this.recompiledFilter = this.query.filter;
    }
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
      // If the user selected a query from the dropdown list (not manually entering it)
      // Set the new expression and filter
      if (!_isEqual(this.prevExpressions, this.query.expressions)) {
        this.prevExpressions = this.query.expressions;
        this.recompiledFilter = this.query.filter;
      }
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
          const queryBuilder = QueryBuilder(this.schema,
            query.expressions, queryMeta, query.onlyExpressionsFilter);
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
        searchTemplate: undefined,
      };

      // There are two cases in which we need to recompile the filter:
      // 1) The force parameter was sent
      // 2) The auto query configuration is turned on and the expression / filter have changed
      const filterShouldRecompile = force
                                    || (this.autoQuery
                                        && ((!_isEqual(this.prevExpressions, query.expressions))
                                            || this.recompiledFilter !== prevFilter));

      let filter;
      // Check if the calculation is forced
      // (using the search button) or the autoQuery value is chosen
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
            onlyExpressionsFilter: filterShouldRecompile
              ? resultFilters.onlyExpressionsFilter
              : this.query.onlyExpressionsFilter,
            expressions: query.expressions,
            meta: queryMeta,
            search: null,
          },
          page: 0,
        },
      });

      // Save the newly entered expression as a previous expression for the next comparison
      this.prevExpressions = _cloneDeep(query.expressions);

      // Fetch the entities only if the filter has changed
      if (prevFilter !== filter && filter) {
        this.recompiledFilter = filter;
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
