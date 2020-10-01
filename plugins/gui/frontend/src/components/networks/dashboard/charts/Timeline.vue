<template>
  <div class="x-chart-timeline">
    <div class="timeline-query-type">
      <ASwitch
        v-model="intersection"
        @change="updateIntersection"
      />
      <span class="x-switch-label">{{ intersection ? 'Intersection' : 'Comparison' }}</span>
    </div>
    <h5 class="mb-1">
      <template v-if="intersection">
        Select a base query and another one to intersect with it:
      </template>
      <template v-else>
        Select up to {{ max }} queries for comparison:
      </template>
    </h5>
    <XSelectViews
      v-model="selectedViews"
      :entities="entities"
      :view-options="viewOptions"
      :chart-view="chartView"
      :intersection="intersection"
      :max="max"
      :min="min"
      :default-chart-colors="defaultChartsColors.lineColors"
    />
    <XSelectTimeframe
      ref="timeframe"
      v-model="timeframe"
    />
  </div>
</template>

<script>
import { TimelineTimeframesTypesEnum, TimelineTimeframesUnitsEnum } from '@constants/charts';
import xSelectViews from '@neurons/inputs/SelectViews.vue';
import xSelectTimeframe from '@neurons/inputs/SelectTimeframe.vue';
import chartMixin from './chart';
import defaultChartsColors from '@constants/colors';
import { Switch as ASwitch } from 'ant-design-vue';

const dashboardView = { name: '', entity: '', chart_color: '' };
export default {
  name: 'XChartTimeline',
  components: {
    XSelectViews: xSelectViews,
    XSelectTimeframe: xSelectTimeframe,
    ASwitch,
  },
  mixins: [chartMixin],
  props: {
    chartView: {
      type: String,
      default: '',
    },
  },
  data() {
    return { defaultChartsColors };
  },
  computed: {
    initConfig() {
      return {
        views: [{ ...dashboardView }],
        timeframe: {
          type: TimelineTimeframesTypesEnum.relative,
          unit: TimelineTimeframesUnitsEnum.days.name,
          count: 7,
        },
        intersection: false,
      };
    },
    intersection: {
      get() {
        return this.config.intersection;
      },
      set(intersection) {
        this.config = { ...this.config, intersection };
      },
    },
    selectedViews: {
      get() {
        return this.config.views;
      },
      set(views) {
        this.config = { ...this.config, views };
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
    max() {
      return (this.intersection) ? 2 : 3;
    },
    min() {
      return this.intersection ? 2 : 1;
    },
  },
  methods: {
    validate() {
      this.$emit('validate', !this.selectedViews.filter((view) => view.id === '').length
          && this.$refs.timeframe.isValid);
    },
    updateIntersection(intersection) {
      const viewsLength = this.config.views.length;
      if (!intersection || viewsLength === 2) return;
      if (viewsLength < 2) {
        this.selectedViews.push({ ...dashboardView });
      }
      this.config = {
        ...this.config,
        intersection,
        views: this.selectedViews.filter((item, i) => i !== 2),
      };
    },
  },
};
</script>

<style lang="scss">
  .x-chart-timeline {
    .timeline-query-type {
      @include x-switch;
      margin-bottom: 16px;
      margin-top: 16px;
    }
  }
</style>
