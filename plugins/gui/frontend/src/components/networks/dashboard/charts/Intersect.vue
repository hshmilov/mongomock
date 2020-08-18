<template>
  <div class="x-chart-metric intersect-wizard">
    <label>Module for chart:</label>
    <XSelectSymbol
      id="module"
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      class="grid-span2"
      @input="updateEntity"
    />

    <label>Base query:</label>
    <div class="grid-span2 field-with-colors-bar">
      <XSelect
        id="baseQuery"
        v-model="base"
        :options="viewOptions(entity, base)"
        :searchable="true"
        placeholder="query (or empty for all)"
        class="view-name"
      />
      <XColorPicker
        v-model="baseChartColor"
        class="color-picker-container"
        :preset-colors="defaultChartsColors"
      />
    </div>

    <label>Intersecting query:</label>
    <div class="grid-span2 field-with-colors-bar">
      <XSelect
        id="intersectingFirst"
        :value="intersecting[0]"
        :options="viewOptions(entity, intersecting[0])"
        :searchable="true"
        placeholder="query..."
        class="grid-span2 intersectingFirst"
        @input="(view) => updateIntersecting(0, view)"
      />
      <XColorPicker
        :value="firstIntersectingColor"
        class="color-picker-container"
        :preset-colors="defaultChartsColors"
        @input="updateColorValue($event, 0 )"
      />
    </div>

    <template v-if="intersecting.length > 1">
      <label>Intersecting query:</label>
      <div class="grid-span2 field-with-colors-bar">
        <XSelect
          id="intersectingSecond"
          class="intersectingSecond"
          :value="intersecting[1]"
          :options="viewOptions(entity, intersecting[1])"
          :searchable="true"
          placeholder="query..."
          @input="(view) => updateIntersecting(1, view)"
        />
        <XColorPicker
          :value="secondIntersectingColor"
          class="color-picker-container"
          :preset-colors="defaultChartsColors"
          @input="updateColorValue($event, 1)"
        />

        <XButton
          type="link"
          @click="removeIntersecting()"
        >
          x
        </XButton>
      </div>
    </template>
    <XButton
      type="light"
      :disabled="hasMaxViews"
      class="grid-span3"
      :title="addBtnTitle"
      @click="addIntersecting"
    >+</XButton>
  </div>
</template>

<script>
import _take from 'lodash/take';
import XColorPicker from '@axons/inputs/ColorPicker.vue';
import XButton from '../../../axons/inputs/Button.vue';
import XSelect from '../../../axons/inputs/select/Select.vue';
import XSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue';
import chartMixin from './chart';
import defaultChartsColors from '../../../../constants/colors';

export default {
  name: 'XChartIntersect',
  components: {
    XButton, XSelect, XSelectSymbol, XColorPicker,
  },
  mixins: [chartMixin],
  data() {
    return {
      max: 2,
      defaultChartsColors: defaultChartsColors.pieColors,
      emptyIntersectingQueryColor: false,
    };
  },
  computed: {
    initConfig() {
      return {
        entity: '',
        base: '',
        base_color: this.defaultChartsColors[0],
        intersecting: [''],
        intersecting_colors: [],
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
        this.config = { ...this.config, base };
      },
    },
    baseChartColor: {
      get() {
        return this.config.base_color || this.defaultChartsColors[0];
      },
      set(color) {
        this.config = { ...this.config, base_color: color };
      },
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
        const intersectionsQueryiesCount = this.intersecting.length;
        const savedIntersectongColors = this.config.intersecting_colors || null;

        if (savedIntersectongColors) {
          const [
            firstIntersectingColor = defaultChartsColors.intersectingColors[0],
            secondIntersectingColor = defaultChartsColors.intersectingColors[1],
          ] = savedIntersectongColors;
          return intersectionsQueryiesCount === 1 ? [savedIntersectongColors[0]] : [
            firstIntersectingColor,
            secondIntersectingColor,
          ];
        }

        return intersectionsQueryiesCount === 1 ? [] : _take(defaultChartsColors.intersectingColors, intersectionsQueryiesCount);
      },
      set(colors) {
        this.config = { ...this.config, intersecting_colors: [...colors] };
      },
    },
    firstIntersectingColor() {
      return this.intersectingColors[0];
    },
    secondIntersectingColor() {
      return this.intersectingColors[1];
    },
    maxIntersections() {
      return this.intersecting.length === this.max + 1;
    },
    hasMaxViews() {
      if (!this.max) return false;
      return this.intersecting.length === this.max;
    },
    addBtnTitle() {
      return this.hasMaxViews
        ? `Limited to ${this.max} intersecting queries`
        : '';
    },
  },
  methods: {
    updateEntity(entity) {
      if (entity === this.entity) return;
      this.config = {
        entity,
        base: '',
        base_color: this.defaultChartsColors[0],
        intersecting: [''],
        intersecting_colors: [],
      };
    },
    removeIntersecting() {
      this.config = {
        ...this.config,
        intersecting: [this.intersecting[0]],
        intersecting_colors: this.firstIntersectingColor ? [this.firstIntersectingColor] : [],
      };
    },
    addIntersecting() {
      this.intersecting = [...this.intersecting, ''];
    },
    updateIntersecting(index, view) {
      this.intersecting = this.intersecting.map((item, ind) => {
        if (ind === index) return view;
        return item;
      });
    },
    validate() {
      this.$emit(
        'validate',
        !this.intersecting.filter((view) => view === '').length,
      );
    },
    updateColorValue(colorHexValue, intersectIndex) {
      this.intersectingColors = this.intersectingColors.map((color, index) => {
        if (intersectIndex === index) { return colorHexValue; } return color;
      });
    },
  },
};
</script>

<style lang="scss">
.intersect-wizard {
  .field-with-colors-bar {
    display: flex;
    .x-dropdown{
      max-width: calc(100% - 114px);
    }
    .color-picker-container {
      margin-left: 5px;
    }
  }
  .view-name,
  .intersectingFirst,
  .intersectingSecond {
    width: 100%;
  }
}
</style>
