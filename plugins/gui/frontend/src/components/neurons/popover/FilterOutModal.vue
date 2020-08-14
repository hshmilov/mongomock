<template>
  <XFeedbackModal
    v-model="isActive"
    :handle-save="filterSelectedEntitiesOutOfQueryResult"
    :message="`${module} were filtered out`"
    :disabled="totalSelectedCharactersForFilterOut >= 10000"
    approve-text="Yes"
  >
    <div
      v-if="totalSelectedCharactersForFilterOut >= 10000"
      class="table-error"
    >Maximum filtered out assets has been reached.
      Please use the query wizard to filter the query</div>
    <div
      v-else
    >
      <h5>Do you wish to continue?</h5>
      <div>The {{ selectionCount }} selected assets will be filtered from this query</div>
    </div>
  </XFeedbackModal>
</template>

<script>
import _get from 'lodash/get';
import { mapMutations, mapState, mapGetters } from 'vuex';
import actionModal from '@mixins/action_modal';
import { filterOutExpression } from '@constants/filter';
import { UPDATE_DATA_VIEW, SHOW_TOASTER_MESSAGE } from '@store/mutations';
import { GET_MODULE_SCHEMA } from '@store/getters';
import XFeedbackModal from './FeedbackModal.vue';
import QueryBuilder from '../../../logic/query_builder';

export default {
  name: 'XFilterOutModal',
  components: { XFeedbackModal },
  mixins: [actionModal],
  computed: {
    ...mapState({
      view(state) {
        return state[this.module].view;
      },
    }),
    ...mapGetters({
      getModuleSchema: GET_MODULE_SCHEMA,
    }),
    schema() {
      return this.getModuleSchema(this.module);
    },
    totalSelectedCharactersForFilterOut() {
      return this.getFilterOutExpressionValue().length;
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    getFilterOutExpressionValue() {
      let entitiesIdsToExclude = this.entities.ids.join(',');
      const prevFilterOutExpression = _get(this.view, 'query.meta.filterOutExpression');
      if (prevFilterOutExpression && !prevFilterOutExpression.showIds) {
        entitiesIdsToExclude = `${entitiesIdsToExclude},${prevFilterOutExpression.value}`;
      }
      return entitiesIdsToExclude;
    },
    getFilterOutExpression() {
      return Object.assign(filterOutExpression, { value: this.getFilterOutExpressionValue() });
    },
    filterSelectedEntitiesOutOfQueryResult() {
      return new Promise((resolve) => {
        try {
          const meta = {
            ...this.view.query.meta,
            filterOutExpression: this.getFilterOutExpression(),
          };
          const expressions = [...this.view.query.expressions];
          const queryBuilder = QueryBuilder(this.schema,
            expressions,
            meta,
            this.view.query.onlyExpressionsFilter);
          const resultFilters = queryBuilder.compileQuery();
          this.updateView({
            module: this.module,
            view: {
              query: {
                filter: resultFilters.resultFilter,
                onlyExpressionsFilter: resultFilters.onlyExpressionsFilter,
                expressions,
                meta,
              },
              page: 0,
            },
          });
          // When the view state is updated fetch the new date using 'done' event
        } catch (error) {
          this.showToasterMessage(error);
        }
        this.$emit('done');
        resolve();
      });
    },
  },
};
</script>

<style lang="scss">

</style>
