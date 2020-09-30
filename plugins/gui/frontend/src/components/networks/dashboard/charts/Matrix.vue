<template>
  <div class="x-chart-matrix x-chart-metric">
    <label class="chart-metric">Module for chart</label>
    <XSelectSymbol
      id="module"
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      class="grid-span2"
      @input="updateEntity"
    />

    <div
      ref="baseQueriesDiv"
      class="base-query-container grid-span3"
    >
      <div
        v-for="(baseItem, index) in base"
        :key="index"
        class="base-query-row"
      >
        <label>Base query</label>
        <XSelect
          :value="baseItem"
          :options="viewOptions(entity, baseItem)"
          :searchable="true"
          placeholder="query (or empty for all)"
          @input="(view) => updateBase(index, view)"
        />
        <XButton
          v-if="index > 0"
          type="link"
          @click="removeBase(index)"
        >x</XButton>
      </div>
    </div>
    <XButton
      id="add-base-query"
      type="light"
      @click="addBase"
    >+</XButton>
    <div class="grid-span2">
      <div
        v-for="(intersectingItem, index) in intersecting"
        :key="index"
        class="intersection-query-row"
      >
        <label>Intersecting query</label>
        <div class="grid-span2 field-with-colors-bar">
          <XSelect
            :value="intersectingItem"
            class="queryField"
            :options="viewOptions(entity, intersectingItem)"
            :searchable="true"
            placeholder="query..."
            @input="(view) => updateIntersecting(index, view)"
          />
          <XColorPicker
            :value="intersectingColors[index] || defaultChartsColors.matrixColor[index]"
            class="color-picker-container"
            :preset-colors="defaultChartsColors.pieColors"
            @input="updateIntersectingColor(index, $event)"
          />
          <XButton
            v-if="index > 0"
            type="link"
            @click="removeIntersecting(index)"
          >x</XButton>
        </div>

      </div>
      <XButton
        v-if="!hasMaxViews"
        id="add-intersecting-query"
        type="light"
        @click="addIntersecting"
      >+</XButton>
    </div>
    <XChartSortSelector
      class="grid-span3"
      :available-sort-types="availableSortTypes"
      :available-sort-orders="availableSortOrders"
      :sort-type.sync="sortType"
      :sort-order.sync="sortOrder"
    />
  </div>
</template>

<script>
import _get from 'lodash/get';
import _take from 'lodash/take';
import _uniq from 'lodash/uniq';
import XColorPicker from '@axons/inputs/ColorPicker.vue';
import XSelect from '../../../axons/inputs/select/Select.vue';
import XSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue';
import chartMixin from './chart';
import XChartSortSelector from '../../../neurons/inputs/ChartSortSelector.vue';
import defaultChartsColors from '../../../../constants/colors';

import {
  ChartSortTypeEnum,
  ChartSortOrderEnum,
} from '../../../../constants/dashboard';

export default {
  name: 'XChartMatrix',
  components: {
    XSelect, XSelectSymbol, XChartSortSelector, XColorPicker,
  },
  mixins: [chartMixin],
  data() {
    return {
      max: 3,
      defaultChartsColors,
    };
  },
  computed: {
    initConfig() {
      return {
        entity: '',
        base: [''],
        intersecting: [''],
        intersecting_colors: [],
        sort: { sort_by: ChartSortTypeEnum.value, sort_order: ChartSortOrderEnum.desc },
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
    base: {
      get() {
        return this.config.base;
      },
      set(base) {
        this.config = { ...this.config, base: [...base] };
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
    availableSortTypes() {
      return [ChartSortTypeEnum.value, ChartSortTypeEnum.name];
    },
    availableSortOrders() {
      return [ChartSortOrderEnum.desc, ChartSortOrderEnum.asc];
    },
    intersecting: {
      get() {
        return this.config.intersecting;
      },
      set(intersecting) {
        this.config = { ...this.config, intersecting: [...intersecting] };
      },
    },
    intersectingColors: {
      get() {
        const savedIntersectingColors = this.config.intersecting_colors || [];
        if (savedIntersectingColors.length) {
          const uniqColorsSet = _uniq([...savedIntersectingColors, ...defaultChartsColors.matrixColor]);
          return _take(uniqColorsSet, this.intersecting.length);
        }
        return _take(defaultChartsColors.matrixColor, this.intersecting.length);
      },
      set(colors) {
        this.config = { ...this.config, intersecting_colors: [...colors] };
      },
    },
    hasMaxViews() {
      if (!this.max) return false;
      return this.intersecting.length === this.max;
    },
    addBtnTitle() {
      return this.hasMaxViews ? `Limited to ${this.max} intersecting queries` : '';
    },
  },
  methods: {
    updateEntity(entity) {
      if (entity === this.entity) return;
      this.config = {
        entity,
        base: [''],
        intersecting: [''],
        intersecting_colors: [],
        sort: { sort_by: ChartSortTypeEnum.value, sort_order: ChartSortOrderEnum.desc },
      };
    },
    removeBase(index) {
      this.base.splice(index, 1);
      this.base = [...this.base];
    },
    addBase() {
      this.base = [...this.base, ''];
      setTimeout(() => {
        this.$refs.baseQueriesDiv.children[this.$refs.baseQueriesDiv.children.length - 1]
          .scrollIntoView();
      });
    },
    updateBase(index, view) {
      this.base = this.base.map((item, ind) => {
        if (ind === index) return view;
        return item;
      });
    },
    removeIntersecting(index) {
      this.config = {
        ...this.config,
        intersecting: this.intersecting.filter((item, i) => i !== index),
        intersecting_colors: this.intersectingColors.filter((item, i) => i !== index),
      };
    },
    addIntersecting() {
      const newIntersecting = [...this.intersecting, ''];
      this.config = {
        ...this.config,
        intersecting: [...newIntersecting],
      };
    },
    updateIntersecting(index, view) {
      this.intersecting = this.intersecting.map((item, ind) => {
        if (ind === index) return view;
        return item;
      });
    },
    updateIntersectingColor(index, color) {
      this.intersectingColors = this.intersectingColors.map((item, i) => {
        if (index === i) { return color; } return item;
      });
    },
    validate() {
      this.$emit('validate', !this.intersecting.filter((view) => view === '').length);
    },
  },
};
</script>

<style lang="scss">
  .x-chart-matrix {
    .base-query-container {
      max-height: 120px;
      @include  y-scrollbar;
      overflow-y: auto;
      margin-right: -8px;
      padding-right: 8px;

      .base-query-row {
        display: flex;
        margin-bottom: 8px;

        label {
          align-self: center;
          margin-right: 100px;
        }

        .x-dropdown  {
          flex-grow: 1;
        }

        button.ant-btn-link {
          margin-left: 6px;
          padding-right: 0;
        }
      }
    }

    .intersection-query-row {
      display: flex;
      margin-bottom: 8px;

      label {
        align-self: center;
        margin-right: 15px;
        min-width: 8em;
      }

      .x-dropdown  {
        flex-grow: 1;
      }

      button.ant-btn-link {
        margin-left: 6px;
        padding-right: 0;
      }
    }

    .sort-container {
      margin-top: 0;
    }

  .field-with-colors-bar {
    display: flex;
    flex-grow: 1;
    max-width: 427px;

    .x-dropdown{
      max-width: calc(100% - 114px);
    }
    .color-picker-container {
      margin-left: 5px;
    }
  }
}
</style>
