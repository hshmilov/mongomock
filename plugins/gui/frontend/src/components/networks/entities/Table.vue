<template>
  <div class="x-entity-table">
    <XQuery
      :module="module"
      :read-only="isReadOnly"
      :default-fields="defaultFields"
      @done="updateEntities"
    />
    <XTable
      ref="table"
      v-model="isReadOnly? undefined: selection"
      :module="module"
      id-field="internal_axon_id"
      :expandable="true"
      :filterable="true"
      :on-click-row="configEntity"
      @input="updateSelection"
    >
      <template #actions>
        <XActionMenu
          v-show="hasSelection"
          :module="module"
          :entities="selection"
          :entities-meta="selectionLabels"
          @done="updateEntities"
        />
        <XTableOptionMenu
          :module="module"
          :default-fields.sync="defaultFields"
          @done="updateEntities"
        />
      </template>
      <template #default="slotProps">
        <XTableData
          v-bind="slotProps"
          :module="module"
        />
      </template>
    </XTable>
  </div>
</template>

<script>
import { mapState, mapMutations, mapActions } from 'vuex';
import { getDefaultTableColumns } from '@api/user-preferences';
import { defaultFields } from '../../../constants/entities';

import XQuery from './query/Query.vue';
import XTable from '../../neurons/data/Table.vue';
import XTableData from './TableData.vue';
import XActionMenu from './ActionMenu.vue';
import XTableOptionMenu from './TableOptionMenu.vue';

import { UPDATE_DATA_VIEW } from '../../../store/mutations';
import {
  FETCH_DATA_FIELDS, FETCH_DATA_CURRENT, FETCH_DATA_HYPERLINKS,
} from '../../../store/actions';

export default {
  name: 'XEntityTable',
  components: {
    XQuery, XTable, XTableData, XActionMenu, XTableOptionMenu,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
  },
  computed: {
    ...mapState({
      isReadOnly(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions[this.module.charAt(0).toUpperCase() + this.module.slice(1)] === 'ReadOnly';
      },
      historicalState(state) {
        return state[this.module].view.historical;
      },
      currentSelectionLabels(state) {
        if (!this.selection.include) return {};
        return state[this.module].content.data
          .filter((entity) => entity && this.selection.ids.includes(entity.internal_axon_id))
          .reduce((entityToLabels, entity) => ({
            ...entityToLabels,
            [entity.internal_axon_id]: entity.labels,
          }), {});
      },
      viewFields(state) {
        return state[this.module].view.fields;
      },
    }),
    hasSelection() {
      return (this.selection.ids && this.selection.ids.length) || this.selection.include === false;
    },
  },
  data() {
    return {
      selection: { ids: [], include: true },
      selectionLabels: {},
      defaultFields: defaultFields[this.module],
    };
  },
  async created() {
    this.fetchDataHyperlinks({ module: this.module });
    const userDefaultTableColumns = await getDefaultTableColumns(this.module);
    if (userDefaultTableColumns.length) {
      this.defaultFields = userDefaultTableColumns;
    }
    if (!this.viewFields.length) {
      this.updateView({
        module: this.module,
        view: {
          fields: this.defaultFields,
        },
      });
      this.$refs.table.fetchContentPages(true);
    }
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    ...mapActions({
      fetchDataFields: FETCH_DATA_FIELDS,
      fetchDataHyperlinks: FETCH_DATA_HYPERLINKS,
      fetchDataCurrent: FETCH_DATA_CURRENT,
    }),
    configEntity(entityId) {
      if (this.hasSelection) return;

      this.$emit('row-clicked');

      let path = `${this.module}/${entityId}`;
      if (this.historicalState) {
        path += `?history=${encodeURIComponent(this.historicalState)}`;
      }
      this.$router.push({ path });
      this.fetchDataCurrent({
        module: this.module,
        id: entityId,
        history: this.historicalState,
      });
    },
    updateEntities(reset = true, selectIds = []) {
      this.$refs.table.fetchContentPages(true);
      this.fetchDataFields({ module: this.module });
      if (reset) {
        this.selection = { ids: selectIds, include: true };
      } else {
        this.updateSelection(this.selection);
      }
    },
    updateSelection(selection) {
      if (!selection.include) {
        this.selectionLabels = {};
      } else {
        this.$nextTick(() => {
          this.selectionLabels = selection.ids
            .reduce((entityToLabels, entity) => ({
              ...entityToLabels,
              [entity]: this.currentSelectionLabels[entity] || this.selectionLabels[entity] || [],
            }), {});
        });
      }
    },
  },
};
</script>

<style lang="scss">
    .x-entity-table {
        height: 100%;
        .x-table-wrapper .actions {
          grid-gap: 0;
          align-items: center;

          > .x-button.link {
            width: 120px;
          }
        }
    }

</style>
