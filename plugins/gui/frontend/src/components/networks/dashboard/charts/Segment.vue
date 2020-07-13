<template>
  <div class="x-chart-metric">
    <XSelectSymbol
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      @input="updateEntity"
    />
    <XSelect
      v-model="view"
      :options="currentViewOptions"
      :searchable="true"
      placeholder="query (or empty for all)"
      class="view-name grid-span2"
    />
    <label>Segment by</label>
    <XSelectTypedField
      v-model="fieldName"
      :options="fieldOptions"
      class="grid-span2"
    />
    <template>
      <label class="filter-by-label">Filter by</label>
      <XFilterContains
        v-model="filters"
        class="grid-span2"
        :options="filterFields"
        :min="1"
      />
    </template>

    <XCheckbox
      v-model="includeEmpty"
      :read-only="isAllowIncludeEmpty"
      label="Include entities with no value"
      class="grid-span3"
    />

    <XCheckbox
      v-model="showTimeline"
      label="Include timeline"
      class="grid-span1"
    />
    <XSelectTimeframe
      v-if="showTimeline"
      ref="timeframe"
      v-model="timeframe"
      class="segment-timeline-timeframe"
    />

    <XChartSortSelector
      v-if="showSortOptions"
      class="grid-span3"
      :available-sort-types="availableSortTypes"
      :available-sort-orders="availableSortOrders"
      :sort-type.sync="sortType"
      :sort-order.sync="sortOrder"
    />

  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import _get from 'lodash/get';
import _isEmpty from 'lodash/isEmpty';
import _cloneDeep from 'lodash/cloneDeep';
import { TimelineTimeframesTypesEnum, TimelineTimeframesUnitsEnum } from '@constants/charts';
import XSelect from '../../../axons/inputs/select/Select.vue';
import XSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue';
import XSelectTypedField from '../../../neurons/inputs/SelectTypedField.vue';
import XSelectTimeframe from '../../../neurons/inputs/SelectTimeframe.vue'
import XFilterContains from '../../../neurons/schema/query/FilterContains.vue';
import XCheckbox from '../../../axons/inputs/Checkbox.vue';
import chartMixin from './chart';
import {
  getParentFromField,
  isObjectListField,
} from '../../../../constants/utils';

import {
  GET_MODULE_SCHEMA,
  GET_DATA_SCHEMA_BY_NAME,
} from '../../../../store/getters';
import {
  ChartSortTypeEnum,
  ChartSortOrderEnum,
  ChartSortOrderLabelEnum, ChartViewEnum,
} from '../../../../constants/dashboard';
import XChartSortSelector from '../../../neurons/inputs/ChartSortSelector.vue';

const initConfigFilter = [{
  name: '', value: '',
}];

const defaultTimeframe = {
  type: TimelineTimeframesTypesEnum.relative,
  unit: TimelineTimeframesUnitsEnum.days.name,
  count: 7,
};

export default {
  name: 'XChartSegment',
  components: {
    XSelect,
    XSelectSymbol,
    XSelectTypedField,
    XCheckbox,
    XFilterContains,
    XChartSortSelector,
    XSelectTimeframe,
  },
  mixins: [chartMixin],
  data() {
    return {
      ChartSortTypeEnum,
      ChartSortOrderEnum,
      ChartSortOrderLabelEnum,
    };
  },
  computed: {
    ...mapGetters({
      getModuleSchema: GET_MODULE_SCHEMA,
      getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME,
    }),
    initConfig() {
      return {
        entity: '',
        view: '',
        field: { name: '' },
        filters: _cloneDeep(initConfigFilter),
        sort: { sort_by: ChartSortTypeEnum.value, sort_order: ChartSortOrderEnum.desc },
        show_timeline: false,
        timeframe: { ...defaultTimeframe },
      };
    },
    entity: {
      get() {
        return this.config.entity;
      },
      set(entity) {
        this.config = { ...this.config, entity };
      },
    },
    view: {
      get() {
        return this.config.view;
      },
      set(view) {
        this.config = { ...this.config, view };
      },
    },
    fieldName: {
      get() {
        return this.config.field.name;
      },
      set(fieldName) {
        if (fieldName === this.config.field.name) {
          return;
        }
        const field = this.schemaByName[fieldName] || { name: '' };
        this.config = {
          ...this.config,
          field,
          value_filter: _cloneDeep(initConfigFilter),
        };
      },
    },
    filters: {
      get() {
        if (_isEmpty(this.config.value_filter)) {
          return _cloneDeep(initConfigFilter);
        }
        if (Array.isArray(this.config.value_filter)) {
          return this.config.value_filter;
        }
        return [
          { name: this.config.field.name, value: this.config.value_filter },
        ];
      },
      set(filters) {
        this.config = {
          ...this.config,
          value_filter: filters,
          include_empty: false,
        };
      },
    },
    includeEmpty: {
      get() {
        return this.config.include_empty;
      },
      set(includeEmpty) {
        this.config = { ...this.config, include_empty: includeEmpty };
      },
    },
    showTimeline: {
      get() {
        return this.config.show_timeline;
      },
      set(showTimeline) {
        const timeframe = this.config.timeframe || { ...defaultTimeframe };
        this.config = {
          ...this.config,
          show_timeline: showTimeline,
          timeframe,
        };
      },
    },
    timeframe: {
      get() {
        return this.config.timeframe;
      },
      set(timeframe) {
        this.config = { ...this.config, timeframe };
      },
    },
    sortType: {
      get() {
        return _get(this.config, 'sort.sort_by', ChartSortTypeEnum.value);
      },
      set(sortType) {
        const sort = { ...this.config.sort };
        sort.sort_by = sortType;
        this.config = { ...this.config, sort };
      },
    },
    sortOrder: {
      get() {
        return _get(this.config, 'sort.sort_order', ChartSortOrderEnum.desc);
      },
      set(sortOrder) {
        const sort = { ...this.config.sort };
        sort.sort_order = sortOrder;
        this.config = { ...this.config, sort };
      },
    },
    fieldOptions() {
      if (!this.entity) return [];
      return this.getModuleSchema(this.entity).map((category) => ({
        ...category,
        fields: category.fields.filter((field) => {
          if (field.name === 'labels') return true;
          if (
            !field.name.startsWith('specific_data')
            && !field.name.startsWith('adapters_data')
          ) {
            return false;
          }
          return !isObjectListField(field);
        }),
      }));
    },
    filterFields() {
      if (this.fieldName === '') {
        return [];
      }
      const parentName = getParentFromField(this.fieldName);
      const parentSchema = this.schemaByName[parentName];
      const isComplexObject = parentSchema && isObjectListField(parentSchema);
      if (!isComplexObject) {
        return [this.config.field];
      }

      const availableFields = Array.isArray(parentSchema.items)
        ? parentSchema.items
        : parentSchema.items.items;
      return availableFields.filter(this.isFieldFilterable).map((option) => ({
        ...option,
        name: `${parentName}.${option.name}`,
      }));
    },
    schemaByName() {
      if (!this.entity) return {};
      return this.getDataSchemaByName(this.entity);
    },
    isAllowIncludeEmpty() {
      return !!this.filters.filter((item) => item.name && item.value).length;
    },
    isFiltersValid() {
      return !this.filters.find((item) => !!item.name !== !!item.value);
    },
    availableSortTypes() {
      return [ChartSortTypeEnum.value, ChartSortTypeEnum.name];
    },
    availableSortOrders() {
      return [ChartSortOrderEnum.desc, ChartSortOrderEnum.asc];
    },
    showSortOptions() {
      return this.chartView === ChartViewEnum.histogram;
    },
    currentViewOptions() {
      return this.viewOptions(this.entity, this.view);
    },
  },
  watch: {
    chartView(view) {
      if (view !== ChartViewEnum.histogram && this.config.sort) {
        this.config.sort = {
          sort_by: ChartSortTypeEnum.value,
          sort_order: ChartSortOrderEnum.desc,
        };
      }
    },
  },
  methods: {
    validate() {
      const isValid = this.fieldName
        && this.isFiltersValid
        && (!this.$refs.timeframe || this.$refs.timeframe.isValid);
      this.$emit('validate', isValid);
    },
    updateEntity(entity) {
      if (entity === this.entity) return;
      this.config = {
        entity,
        view: '',
        field: {
          name: '',
        },
        value_filter: _cloneDeep(initConfigFilter),
        sort: { sort_by: ChartSortTypeEnum.value, sort_order: ChartSortOrderEnum.desc },
        show_timeline: false,
        timeframe: defaultTimeframe,
      };
    },
    isFieldFilterable(field) {
      const isFieldChildOfComplexObject = field.branched;
      const isFieldNotDateOrArrayOfDates = field.format !== 'date-time'
        && (!field.items || field.items.format !== 'date-time');
      return (
        !isFieldChildOfComplexObject
        && isFieldNotDateOrArrayOfDates
        && !isObjectListField(field)
      );
    },
  },
};
</script>

<style lang="scss">
.x-chart-metric {
  .filter-by-label {
    align-self: flex-start;
    margin-top: 14px;
  }

  .segment-timeline-timeframe {
    .x-select-timeframe_config--limited {
      margin-top: auto;
    }
  }
}
</style>
