<template>
  <XActionMenu
    :module="module"
    :entities="entities"
    :entities-meta="entitiesMeta"
    :disabled="disabled"
    @done="onDone"
  >
    <XActionMenuItem
      :title="`Link ${module}`"
      :handle-save="linkEntities"
      :message="`${module} were linked`"
      action-text="Save"
      :disabled="selectionCount > 10"
    >
      <div
        v-if="selectionCount > 10"
        class="table-error"
      >Maximal amount of {{ module }} to link is 10</div>
      <div
        v-else
        class="warn-delete"
      >You are about to link {{ selectionCount }} {{ module }}.</div>
    </XActionMenuItem>
    <XActionMenuItem
      :title="`Unlink ${module}`"
      :handle-save="unlinkEntities"
      :message="`${module} were unlinked`"
      action-text="Save"
    >
      <div class="warn-delete">
        You are about to unlink {{ selectionCount }} {{ module }}.
        This means that each of the adapter {{ module }}
        inside will become a standalone axonius entity.
      </div>
    </XActionMenuItem>
    <XActionMenuItem
      v-if="!enforcementRestricted"
      title="Enforce"
      :handle-save="enforceEntities"
      :message="`Enforcement is running. View in Enforcements -> Tasks`"
      action-text="Run"
    >
      <div class="mb-8">
        There are {{ selectionCount }} {{ module }} selected. Select the Enforcement Set:
      </div>
      <XSelect
        v-model="selectedEnforcement"
        :options="enforcementOptions"
      />
    </XActionMenuItem>
    <XActionMenuItem
      title="Filter out from query results"
      :handle-save="filterSelectedEntitiesOutOfQueryResult"
      :message="`${module} were filtered out`"
      :disable-link="isAllSelected"
      :disabled="totalSelectedCharactersForFilterOut >= 10000"
      disabled-description="Select all is not applicable. Please use the query wizard to filter the query"
      action-text="Yes"
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
    </XActionMenuItem>
  </XActionMenu>
</template>

<script>
import {
  mapState, mapActions, mapGetters, mapMutations,
} from 'vuex';
import _get from 'lodash/get';
import XActionMenu from '../../neurons/data/ActionMenu.vue';
import XActionMenuItem from '../../neurons/data/ActionMenuItem.vue';
import XSelect from '../../axons/inputs/select/Select.vue';

import {
  ADD_DATA_LABELS, LINK_DATA, UNLINK_DATA, ENFORCE_DATA, FETCH_DATA_CONTENT,
} from '../../../store/actions';

import { filterOutExpression } from '../../../constants/filter';
import { GET_MODULE_SCHEMA } from '../../../store/getters';

import { UPDATE_DATA_VIEW, SHOW_TOASTER_MESSAGE } from '../../../store/mutations';
import QueryBuilder from '../../../logic/query_builder';


export default {
  name: 'XEntitiesActionMenu',
  components: { XActionMenu, XActionMenuItem, XSelect },
  props: {
    module: {
      type: String,
      required: true,
    },
    entities: {
      type: Object,
      default: () => ({}),
    },
    entitiesMeta: {
      type: Object,
      default: () => ({}),
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      selectedEnforcement: '',
    };
  },
  computed: {
    ...mapState({
      dataCount(state) {
        return state[this.module].count.data;
      },
      enforcementOptions(state) {
        return state.enforcements.content.data.map((enforcement) => ({
          name: enforcement.name, title: enforcement.name,
        }));
      },
      enforcementRestricted() {
        return this.$cannot(this.$permissionConsts.categories.Enforcements,
          this.$permissionConsts.actions.View);
      },
      view(state) {
        return state[this.module].view;
      },
    }),
    ...mapGetters({
      getModuleSchema: GET_MODULE_SCHEMA,
    }),
    isAllSelected() {
      return this.entities.include !== undefined && !this.entities.include;
    },
    selectionCount() {
      if (this.entities.include === undefined || this.entities.include) {
        return this.entities.ids.length;
      }
      return this.dataCount - this.entities.ids.length;
    },
    totalSelectedCharactersForFilterOut() {
      return this.getFilterOutExpressionValue().length;
    },
    schema() {
      return this.getModuleSchema(this.module);
    },
  },
  mounted() {
    if (!this.enforcementRestricted && !this.enforcementOptions.length) {
      this.fetchContent({
        module: 'enforcements',
        getCount: false,
      });
    }
  },
  methods: {
    ...mapActions(
      {
        addLabels: ADD_DATA_LABELS,
        linkData: LINK_DATA,
        unlinkData: UNLINK_DATA,
        enforceData: ENFORCE_DATA,
        fetchContent: FETCH_DATA_CONTENT,
      },
    ),
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    linkEntities() {
      return this.linkData({
        module: this.module, data: this.entities,
      }).then(() => this.$emit('done'));
    },
    unlinkEntities() {
      return this.unlinkData({
        module: this.module, data: this.entities,
      }).then(() => this.$emit('done'));
    },
    enforceEntities() {
      return this.enforceData({
        module: this.module,
        data: {
          name: this.selectedEnforcement, ...this.entities,
        },
      });
    },
    onDone(reset) {
      this.$emit('done', reset);
    },
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
          const recompile = false;
          const resultFilters = queryBuilder.compileQuery(recompile);
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
  .x-form.expand .item {
    width: 100%;

    .object {
      width: 100%;
    }
  }
</style>
