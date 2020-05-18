<template>
  <div class="x-table">
    <table class="table">
      <thead>
        <tr class="clickable">
          <th
            v-if="value && multipleRowSelection"
            class="w-14"
          >
            <XCheckbox
              :data="allSelected"
              :indeterminate="partSelected"
              @change="onSelectAll"
            />
          </th>
          <th
            v-if="expandable"
            class="w-14"
          >
            <div>&nbsp;</div>
          </th>
          <XTableHead
            v-for="field in fields"
            :key="field.name"
            :field="field"
            :sort="sort"
            :sortable="sortable(field)"
            :filters="getFilters(field.name)"
            :filterable="filterable"
            :filter-column-name="filterColumnName"
            @click="clickCol"
            @toggleColumnFilter="(fieldName) => toggleColumnFilter(fieldName)"
          />
        </tr>
      </thead>
      <tbody>
        <XTableRow
          v-for="(row, index) in data"
          :id="row[idField]"
          :key="index"
          :data="row"
          :fields="fields"
          :sort="sort"
          :filters="colFilters"
          :selected="value && value.includes(row[idField])"
          :expandable="expandable"
          :clickable="onClickRow !== undefined"
          :read-only="readOnly.includes(row[idField])"
          :row-class="rowClass"
          :format-title="formatTitle"
          :multiple-row-selection="multipleRowSelection"
          @input="(selected) => onSelect(row[idField], selected)"
          @click.native="() => clickRow(row[idField])"
        >
          <template #default="slotProps">
            <slot v-bind="slotProps">
              <XTableData
                v-if="!$scopedSlots.default"
                v-bind="slotProps"
              />
            </slot>
          </template>
        </XTableRow>
        <template v-if="pageSize">
          <tr
            v-for="n in pageSize - data.length"
            :key="data.length + n"
            class="x-table-row"
          >
            <td v-if="value && multipleRowSelection">
&nbsp;
            </td>
            <td v-if="expandable">
&nbsp;
            </td>
            <td
              v-for="field in fields"
              :key="field.name"
            >&nbsp;</td>
          </tr>
        </template>
      </tbody>
    </table>
    <ColumnFilter
      v-if="filterColumnActive"
      :filter-column-name="filterColumnName"
      :saved-filters="getFilters(filterColumnName)"
      @updateColFilters="data => $emit('updateColFilters', data)"
      @toggleColumnFilter="toggleColumnFilter"
    />
  </div>
</template>

<script>
import XTableData from './TableData';
import XTableHead from './TableHead.vue';
import XTableRow from './TableRow.vue';
import XCheckbox from '../inputs/Checkbox.vue';
import ColumnFilter from './ColumnFilter.vue';

export default {
  name: 'XTable',
  components: {
    XTableHead, XTableRow, XTableData, XCheckbox, ColumnFilter,
  },
  props: {
    fields: {
      type: Array,
      required: true,
    },
    data: {
      type: [Object, Array],
      required: true,
    },
    pageSize: {
      type: Number,
      default: null,
    },
    sort: {
      type: Object,
      default: () => ({ field: '', desc: true }),
    },
    colFilters: {
      type: Object,
      default: undefined,
    },
    idField: {
      type: String,
      default: 'uuid',
    },
    value: {
      type: Array,
      default: undefined,
    },
    expandable: {
      type: Boolean,
      default: false,
    },
    filterable: {
      type: Boolean,
      default: false,
    },
    onClickRow: {
      type: Function,
      default: undefined,
    },
    onClickCol: {
      type: Function,
      default: undefined,
    },
    onClickAll: {
      type: Function,
      default: undefined,
    },
    readOnly: {
      type: Array,
      default: () => [],
    },
    rowClass: {
      type: [Function, String],
      default: '',
    },
    formatTitle: {
      type: Function,
      default: null,
    },
    multipleRowSelection: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      filterColumnActive: false,
      filterColumnName: '',
    };
  },
  computed: {
    ids() {
      return this.data.map((item) => item[this.idField]);
    },
    partSelected() {
      return Boolean(this.value && this.value.length && this.value.length < this.data.length);
    },
    allSelected() {
      return Boolean(this.value && this.value.length && this.value.length === this.data.length);
    },
  },
  methods: {
    clickRow(id) {
      if (!this.onClickRow || this.readOnly.includes(id)) return;
      if (!document.getSelection().isCollapsed) return;

      this.onClickRow(id);
    },
    clickCol(name) {
      if (!this.onClickCol) return;

      this.onClickCol(name);
    },
    onSelect(id, isSelected) {
      if (isSelected) {
        this.$emit('input', [...this.value, id]);
      } else {
        this.$emit('input', this.value.filter((currentId) => currentId !== id));
      }
    },
    onSelectAll(selected) {
      if (selected && (!this.value || !this.value.length)) {
        this.$emit('input', this.ids.filter((id) => !this.readOnly.includes(id)));
      } else {
        this.$emit('input', []);
      }
      if (this.onClickAll) {
        this.onClickAll(selected);
      }
    },
    getFilters(fieldName) {
      if (!this.colFilters) {
        return undefined;
      }
      return this.colFilters[fieldName] || [];
    },
    sortable(field) {
      return (this.onClickCol !== undefined) && field.name !== 'adapters';
    },
    toggleColumnFilter(fieldName) {
      this.filterColumnName = fieldName;
      this.filterColumnActive = !this.filterColumnActive;
    },
  },
};
</script>

<style lang="scss">
  .x-table {
    position: relative;
    height: calc(100% - 48px);
    overflow-y: auto;

    .table {
      border-collapse: collapse;

      thead {
        tr {
          th {
            position: sticky;
            top: 0;
            background: $theme-white;
            line-height: 28px;
            color: $theme-black;
            box-shadow: 8px 0 4px 0 $grey-2;
            z-index: 5;
          }
        }
      }

      .array.inline .item:first-child.v-chip {
        margin-left: -12px;
      }
    }
  }

</style>
