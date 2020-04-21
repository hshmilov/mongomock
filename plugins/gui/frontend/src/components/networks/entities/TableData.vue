<template>
  <div>
    <div
      class="x-data"
      @mouseover="onHoverData"
      @mouseleave="onLeaveData"
    >
      <XTableData
        :schema="schema"
        :data="data"
        :sort="sort"
        :filter="filter"
      />
      <div class="data-table-container">
        <XTooltip v-if="hoverData">
          <XTable
            slot="body"
            v-bind="adaptersDetailsTable"
          />
        </XTooltip>
      </div>
      <div class="details-table-container">
        <MdIcon
          v-if="showExpand"
          class="trigger"
          :class="{active: expandData}"
          @click.native.stop="toggleCell"
        >
          <template v-if="expandData">
            chevron_left
          </template>
          <template v-else>
            chevron_right
          </template>
        </MdIcon>
        <div
          ref="popup"
          class="popup"
          :class="{ top: position.top, left: position.left }"
          @click.stop=""
        >
          <div
            v-if="expandData"
            class="content"
          >
            <XTable v-bind="detailsTable">
              <template #default="slotProps">
                <XTableData
                  v-bind="slotProps"
                  :module="module"
                />
              </template>
            </XTable>
          </div>
        </div>
      </div>
    </div>
    <div
      v-if="expandRow"
      class="details-list-container"
    >
      <div class="list">
        <XTableData
          v-for="(detail, index) in details"
          :key="index"
          :schema="schema"
          :data="detail"
          :sort="sort"
          :filter="filter"
          class="item"
        />
      </div>
    </div>
  </div>
</template>

<script>
import _isEmpty from 'lodash/isEmpty';
import _orderBy from 'lodash/orderBy';
import { mapState, mapGetters } from 'vuex';
import XTable from '../../axons/tables/Table.vue';
import XTableData from '../../neurons/data/TableData';
import XTooltip from '../../axons/popover/Tooltip.vue';
import { pluginMeta } from '../../../constants/plugin_meta';

import { GET_CONNECTION_LABEL } from '../../../store/getters';

export default {
  name: 'XEntityTableData',
  components: {
    XTable,
    XTableData,
    XTooltip,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    schema: {
      type: Object,
      required: true,
    },
    data: {
      type: Object,
      required: true,
    },
    sort: {
      type: Object,
      default: () => ({
        field: '', desc: true,
      }),
    },
    filter: {
      type: String,
      default: '',
    },
    hoverRow: {
      type: Boolean,
      default: false,
    },
    expandRow: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      hoverData: false,
      expandData: false,
      position: {
        top: false,
        left: false,
      },
    };
  },
  computed: {
    ...mapState({
      adaptersSchema(state) {
        return state[this.module].fields.data.generic[0];
      },
    }),
    ...mapGetters({
      getConnectionLabel: GET_CONNECTION_LABEL,
    }),
    fieldName() {
      return this.schema.name;
    },
    adaptersFieldName() {
      return this.adaptersSchema.name;
    },
    isAdaptersField() {
      return this.fieldName === this.adaptersFieldName;
    },
    adaptersLength() {
      return this.data[this.adaptersFieldName].length;
    },
    showExpand() {
      return (this.hoverRow || this.expandData) && this.adaptersLength > 1 && this.fieldName.includes('specific_data')
      && !this.fieldName.includes('_preferred') && !_isEmpty(this.data[this.fieldName]);
    },
    adaptersList() {
      return this.data[this.adaptersFieldName].concat().map((adapter) => [adapter]).sort();
    },
    adaptersDetailsWithClientIdList() {
      return this.data[this.adaptersFieldName].concat().map((adapter, index) => ({
        pluginName: [adapter],
        clientId: this.data['meta_data.client_used'][index],
      })).sort((a, b) => ((a.pluginName[0] > b.pluginName[0]) ? 1 : -1));
    },
    details() {
      if (this.isAdaptersField) {
        return this.adaptersList;
      }
      // auto generated fields that are not saved in the db (Like _preferred fields) dont have _details
      if (this.data[`${this.fieldName}_details`] !== undefined) {
        return this.data[`${this.fieldName}_details`];
      }
      // If you just want the aggregated value to be on top when expanding, return a list with '' the size of adapters list
      return this.data.adapter_list_length_details;
    },
    detailsTable() {
      const baseTable = {
        fields: [
          this.adaptersSchema,
          this.schema,
        ],
        data: this.details.map((detail, i) => ({
          [this.adaptersFieldName]: this.adaptersList[i],
          [this.fieldName]: detail,
        })),
        colFilters: {
          [this.schema.name]: this.filter,
        },
        filterable: false,
      };
      if (this.schema.type === 'string' && this.schema.format === 'date-time') {
        baseTable.fields.push({
          name: 'days', title: 'Days', type: 'integer',
        });
        baseTable.data = baseTable.data.map((item) => {
          if (!item[this.schema.name]) return item;
          const nowDate = new Date();
          nowDate.setHours(0, 0, 0, 0);
          const itemDate = new Date(item[this.schema.name]);
          itemDate.setHours(0, 0, 0, 0);
          return {
            ...item,
            days: Math.ceil((nowDate.getTime() - itemDate.getTime()) / 60 / 60 / 24 / 1000),
          };
        }).sort((a, b) => {
          if (_isEmpty(a[this.schema.name])) return 1;
          if (_isEmpty(b[this.schema.name])) return -1;
          return (new Date(b[this.schema.name]) - new Date(a[this.schema.name]));
        });
      }
      return baseTable;
    },
    adaptersDetailsTable() {
      return {
        fields: [
          this.schema, {
            name: 'name', title: 'Name', type: 'string',
          }],
        data: _orderBy(this.adaptersDetailsWithClientIdList.map((adapter) => {
          let connectionLabel = this.getConnectionLabel(adapter.clientId, adapter.pluginName[0], undefined);
          if (connectionLabel !== '') {
            connectionLabel = ` - ${connectionLabel}`;
          }
          const name = (pluginMeta[adapter.pluginName[0]] ? pluginMeta[adapter.pluginName[0]].title
            : adapter.pluginName[0]) + connectionLabel;
          return {
            [this.fieldName]: adapter.pluginName,
            name,
          };
        }), [this.fieldName]),
        colFilters: {
          [this.schema.name]: this.filter,
        },
        filterable: false,
      };
    },
  },
  methods: {
    toggleCell() {
      this.expandData = !this.expandData;
      if (this.expandData) {
        this.$nextTick(() => {
          const boundingBox = this.$refs.popup.getBoundingClientRect();
          this.position = {
            top: this.position.top || Boolean(boundingBox.bottom > window.innerHeight - 80),
            left: this.position.left || Boolean(boundingBox.right > window.innerWidth - 24),
          };
        });
      }
    },
    onHoverData() {
      if (!this.isAdaptersField) {
        return;
      }
      this.hoverData = true;
    },
    onLeaveData() {
      this.hoverData = false;
    },
  },
};
</script>

<style lang="scss">
  .x-data {
    display: flex;

    .details-table-container {
      min-width: 24px;
      position: relative;

      .trigger {
        font-size: 16px !important;
        border: 1px solid $theme-black;
        border-radius: 100%;
        height: 14px;
        min-width: 14px;
        width: 14px;
        margin-left: 4px;
        transition: all .4s cubic-bezier(.4,0,.2,1);
        &:hover, &.active {
          border-color: $theme-orange;
        }
      }

      .popup {
        overflow: visible;
        position: absolute;
        width: min-content;
        z-index: 200;
        cursor: default;

        &.top {
          bottom: 100%;
        }
        &.left {
          right: 0;
        }

        .content {
          background-color: $theme-white;
          box-shadow: $popup-shadow;
          padding: 4px;
          border-radius: 4px;
          max-height: 30vh;
          animation: horizontal-fade .6s ease-in;

          @keyframes horizontal-fade {
            from {
              transform: translateX(-100%);
              opacity: 0;
            }
          }

          .x-table {
            width: min-content;
            max-height: calc(30vh - 8px);
          }
        }
      }
    }

    .data-table-container {
      position: relative;
    }
  }

  .details-list-container {
    overflow: visible;
    margin: 0px -8px;
    animation: vertical-fade .6s ease-in-out;

    @keyframes vertical-fade {
      from {
        opacity: 0;
        transform: translateY(-50%);
      }
    }

    .list {
      margin-top: 2px;
      padding-left: 8px;
      display: grid;
      grid-gap: 2px 0;
      background-color: rgba($grey-2, 0.6);

      > .item {
        height: 30px;
        display: flex;
        align-items: center;
        border-bottom: 2px solid $theme-white;
        padding: 4px 8px;

        &:last-child {
          border: none;
        }
      }
    }
  }
</style>
