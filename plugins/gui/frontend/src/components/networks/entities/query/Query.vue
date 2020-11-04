<template>
  <div class="x-query">
    <XQueryState
      :module="module"
      :valid="filterValid"
      :read-only="readOnly"
      :user-fields-groups="userFieldsGroups"
      @done="$emit('done')"
      @reset-search="onResetQueryState"
    />
    <div class="filter">
      <XQuerySearchInput
        ref="searchInput"
        v-model="queryFilter"
        :module="module"
        :query-search.sync="query.search"
        :updated-by-wizard.sync="updatedByWizard"
        :user-fields-groups="userFieldsGroups"
        @validate="onValid"
        @done="$emit('done')"
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
        @done="$emit('done', false)"
      />
    </div>
  </div>
</template>

<script>
import { mapState, mapGetters, mapMutations } from 'vuex';
import _isEmpty from 'lodash/isEmpty';

import { AUTO_QUERY, GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL, GET_SAVED_QUERY_BY_NAME } from '@store/getters';
import { UPDATE_DATA_VIEW } from '@store/mutations';
import { expression } from '@constants/filter';

import XQueryState from './State.vue';
import XQuerySearchInput from './SearchInput.vue';
import XQueryWizard from './Wizard.vue';
import QueryBuilder from '../../../../logic/query_builder';

export default {
  name: 'XQuery',
  components: {
    XQueryState, XQuerySearchInput, XQueryWizard,
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
      updatedByWizard: false,
    };
  },
  computed: {
    ...mapState({
      view(state) {
        return state[this.module].view;
      },
      selectedView(state) {
        return state[this.module].selectedView;
      },
      isPredefined(state) {
        const { uuid } = this.selectedView || {};
        if (!uuid) return false;
        const currentView = state[this.module].views.saved.content.data
          .find((view) => view.uuid === uuid);
        return currentView && currentView.predefined;
      },
    }),
    ...mapGetters({
      autoQuery: AUTO_QUERY,
      getModuleSchemaWithConnectionLabel: GET_MODULE_SCHEMA_WITH_CONNECTION_LABEL,
      getSavedQueryById: 'getSavedQueryById',
    }),
    query: {
      get() {
        const { query } = this.view;
        if (_isEmpty(query.expressions)) {
          return { ...query, expressions: [{ ...expression }] };
        }
        return query;
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
        searchTemplate: undefined,
      };

      // If we chose saved query, and we didn't save our original view yet, we need to recompile in
      // order to get it - so we will know when it got changed.
      const recompileForOriginalView = this.selectedView && !this.selectedView.recompiledFilter;
      const filterShouldRecompile = force || this.autoQuery || recompileForOriginalView;

      let filter;
      let selectedView;

      // We need to recompile the query in any case (even if not auto query)
      // In order to check if there is an error
      let resultFilters = {};
      let recompiledFilter;
      resultFilters = this.compileFilter(query, recompiledFilter, queryMeta);

      // Check if we actually want to update the view with the modified recompiled query
      // (using the search button) or the autoQuery value is chosen
      if (filterShouldRecompile) {
        recompiledFilter = resultFilters.resultFilter;

        // Only if the user selected a predefined query
        // It can be either from the devices/users queries or from the saved queries page
        if (this.selectedView && this.isPredefined
              && (!queryMeta.filterOutExpression || !queryMeta.filterOutExpression.value)) {
          // If this is the first time recompiling this query, and a pre-existing filter was chosen,
          // We set the newly recompiled filter as our original one.
          // Otherwise we take the existing one
          const originalRecompiledFilter = !this.selectedView.recompiledFilter
                                           && this.selectedView.filter
            ? recompiledFilter : this.selectedView.recompiledFilter;

          // If the recompiled filter is equal to the original recompiled filter,
          // The filter value should be the original filter.
          // Otherwise, we set the newly recompiled filter.
          filter = originalRecompiledFilter === recompiledFilter
            ? this.selectedView.filter : recompiledFilter;

          selectedView = { ...this.selectedView, recompiledFilter: originalRecompiledFilter };
        // Otherwise, we maintain the original behavior of the code, simply taking the recompiled
        // filter, and not updating anything related to the selected view
        } else {
          filter = recompiledFilter;
        }
      }

      let selectIds = [];
      if (queryMeta && queryMeta.filterOutExpression && queryMeta.filterOutExpression.showIds) {
        selectIds = queryMeta.filterOutExpression.value.split(',');
        queryMeta.filterOutExpression = null;
      }

      // Set indication that the query was updated by the query wizard
      this.updatedByWizard = true;

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
        selectedView,
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
            expressions: [{ ...expression }],
            search: null,
          },
        },
        selectedView: null,
      });
      this.$emit('done');
    },
    onResetQueryState() {
      this.$refs.searchInput.resetSearchInput();
      this.error = null;
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
