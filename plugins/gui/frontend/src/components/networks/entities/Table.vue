<template>
  <div class="x-entity-table">
    <XRoleGateway
      :permission-category="permissionCategory"
    >
      <template slot-scope="{ canView, canUpdate }">
        <XQuery
          v-if="!viewOnly"
          :module="module"
          :read-only="!canView"
          :user-fields-groups="userFieldsGroups"
          @done="updateEntities"
        />
        <XTable
          ref="table"
          v-model="!canUpdate || viewOnly? undefined: selection"
          :module="module"
          :fields="viewFieldsToSchema"
          :fetch-fields="fields"
          id-field="internal_axon_id"
          :expandable="true"
          :filterable="true"
          :on-click-row="configEntity"
          :experimental-api="isExperimentalAPI"
          @input="updateSelection"
        >
          <slot
            slot="actions"
            name="actions"
          >
            <XActionMenu
              :disabled="!canUpdate"
              :module="module"
              :entities="selection"
              :entities-meta="selectionLabels"
              @done="updateEntities"
            />
            <XTableOptionMenu
              :module="module"
              :user-fields-groups.sync="userFieldsGroups"
              :disable-export-csv="!canView"
              @done="updateEntities"
            />
          </slot>
          <template #default="slotProps">
            <XTableData
              v-bind="slotProps"
              :module="module"
            />
          </template>
        </XTable>
      </template>
    </XRoleGateway>
  </div>
</template>

<script>
import {
  mapActions, mapGetters, mapMutations, mapState,
} from 'vuex';
import { getUserTableColumnGroups } from '@api/user-preferences';
import _isEmpty from 'lodash/isEmpty';
import { defaultFields, getEntityPermissionCategory } from '@constants/entities';
import _get from 'lodash/get';

import XQuery from './query/Query.vue';
import XTable from '../../neurons/data/Table.vue';
import XTableData from './TableData.vue';
import XActionMenu from './ActionMenu.vue';
import XTableOptionMenu from './TableOptionMenu.vue';

import { GET_DATA_SCHEMA_BY_NAME } from '../../../store/getters';
import { UPDATE_DATA_VIEW } from '../../../store/mutations';
import {
  FETCH_DATA_FIELDS, FETCH_DATA_CURRENT, FETCH_DATA_HYPERLINKS,
} from '../../../store/actions'
import { LAZY_FETCH_ADAPTERS_CLIENT_LABELS } from '../../../store/modules/adapters';

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
    viewOnly: {
      type: Boolean,
      default: false,
    },
    fields: {
      type: Array,
      default: null,
    },
  },
  data() {
    return {
      selection: { ids: [], include: true },
      selectionLabels: {},
      userFieldsGroups: { default: defaultFields[this.module] },
    };
  },
  computed: {
    ...mapState({
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
      isExperimentalAPI(state) {
        const featureFlagsConfigs = _get(state, 'settings.configurable.gui.FeatureFlags.config', null);
        return (featureFlagsConfigs && featureFlagsConfigs.experimental_api);
      },
    }),
    permissionCategory() {
      return getEntityPermissionCategory(this.module);
    },
    hasSelection() {
      return !_isEmpty(this.selection.ids) || this.selection.include === false;
    },
    ...mapGetters({
      getFieldSchemaByName: GET_DATA_SCHEMA_BY_NAME,
    }),
    schemaFieldsByName() {
      return this.getFieldSchemaByName(this.module);
    },
    viewFieldsToSchema() {
      const { schemaFieldsByName } = this;
      if (!schemaFieldsByName || !Object.keys(schemaFieldsByName).length) {
        return [];
      }
      const fieldsToUse = this.fields ? this.fields : this.viewFields;
      return fieldsToUse.map((fieldName) => schemaFieldsByName[fieldName]).filter((field) => field);
    },
  },
  async created() {
    this.fetchDataHyperlinks({ module: this.module });
    await this.fetchConnectionLabels();
    // get all saved user defined columns group
    const userDefaultTableColumns = await getUserTableColumnGroups(this.module);
    if (userDefaultTableColumns) {
      this.userFieldsGroups = {
        ...this.userFieldsGroups,
        ...userDefaultTableColumns,
      };
    }
    await this.fetchDataFields({ module: this.module });
    if (!this.viewFields.length && !this.fields) {
      this.updateView({
        module: this.module,
        view: {
          fields: this.filterViewFields(this.userFieldsGroups.default),
        },
      });
    }
    this.$refs.table.fetchContentPages();
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    ...mapActions({
      fetchDataFields: FETCH_DATA_FIELDS,
      fetchDataHyperlinks: FETCH_DATA_HYPERLINKS,
      fetchConnectionLabels: LAZY_FETCH_ADAPTERS_CLIENT_LABELS,
      fetchDataCurrent: FETCH_DATA_CURRENT,
    }),
    configEntity(entityId) {
      if (this.hasSelection) return;

      this.$emit('row-clicked');

      let path = `/${this.module}/${entityId}`;
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
    filterViewFields(fields) {
      return fields.filter((fieldName) => this.schemaFieldsByName[fieldName]);
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

          > .x-button.ant-btn-link {
            width: 120px;
          }
        }
        .ant-btn.x-button {
          &.entityMenu:not([disabled]) {
            width: 128px;
            color: $theme-black;
            svg {
              stroke: $theme-black;
            }
            &.menuOpened {
              color: $theme-blue;
              svg {
                stroke: $theme-blue;
              }
            }
            &.action {
              width: auto;
            }
          }
          &.entityMenu:not([disabled]):hover {
            color: $theme-blue;
            svg {
              stroke: $theme-blue;
            }
          }
          &.entityMenuInactive {
            cursor: initial;
            width: auto;
            color: #00000040;
            svg {
              stroke: #00000040;
            }
          }
        }
    }
</style>
