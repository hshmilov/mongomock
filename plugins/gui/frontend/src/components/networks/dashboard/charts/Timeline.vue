<template>
  <div class="x-chart-timeline">
    <md-switch
      v-model="intersection"
      class="md-primary"
      @change="updateIntersection"
    >{{ intersection? 'Intersection' : 'Comparison' }}
    </md-switch>
    <h5
      v-if="intersection"
    >Select a base query and another one to intersect with it:</h5>
    <h5
      v-else
    >Select up to {{ max }} queries for comparison:</h5>
    <x-select-views
      v-model="selectedViews"
      :entities="entities"
      :views="views"
      :max="max"
      :min="min"
    />
    <x-select-timeframe
      v-model="timeframe"
      ref="timeframe"
    />
  </div>
</template>

<script>
  import xSelectViews from '../../../neurons/inputs/SelectViews.vue'
  import xSelectTimeframe from '../../../neurons/inputs/SelectTimeframe.vue'
  import chartMixin from './chart'

  const dashboardView = { name: '', entity: '' }
  export default {
    name: 'XChartTimeline',
    components: {
      xSelectViews, xSelectTimeframe
    },
    mixins: [chartMixin],
    computed: {
      initConfig () {
        return {
          views: [{ ...dashboardView }],
          timeframe: {
            type: 'absolute', from: null, to: null
          },
          intersection: false
        }
      },
      intersection: {
        get () {
          return this.config.intersection
        },
        set (intersection) {
          this.config = { ...this.config, intersection }
        }
      },
      selectedViews: {
        get () {
          return this.config.views
        },
        set (views) {
          this.config = { ...this.config, views}
        }
      },
      timeframe: {
        get () {
          return this.config.timeframe
        },
        set (timeframe) {
          this.config = { ...this.config, timeframe }
        }
      },
      max () {
        return (this.intersection)? 2 : 3
      },
      min () {
        return this.intersection ? 2 : 1
      }
    },
    methods: {
      validate () {
        this.$emit('validate', !this.selectedViews.filter(view => view.name === '').length
          && this.$refs.timeframe.isValid)
      },
      updateIntersection(intersection) {
        let viewsLength = this.config.views.length
        if (!intersection || viewsLength === 2) return
        if (viewsLength < 2) {
          this.selectedViews.push({ ...dashboardView })
        }
        this.selectedViews.splice(2)
      }
    }
  }
</script>

<style lang="scss">

</style>