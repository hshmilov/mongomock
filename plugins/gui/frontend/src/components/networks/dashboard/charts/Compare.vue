<template>
  <div class="x-chart-compare">
    <h5>Select up to {{ max }} queries for comparison:</h5>
    <x-select-views
      v-model="selectedViews"
      :entities="entities"
      :views="views"
      :max="max"
      :min="1"
    />
  </div>
</template>

<script>
  import chartMixin from './chart'
  import xSelectViews from '../../../neurons/inputs/SelectViews.vue'

  const dashboardView = { name: '', entity: '' }
  export default {
    name: 'XChartCompare',
    components: {
      xSelectViews
    },
    mixins: [chartMixin],
    data () {
      return {
        max: 5
      }
    },
    computed: {
      initConfig () {
        return {
          views: [{ ...dashboardView }, { ...dashboardView }]
        }
      },
      selectedViews: {
        get () {
          return this.config.views
        },
        set (views) {
          this.config = { ...this.config, views}
        }
      }
    },
    methods: {
      validate () {
        this.$emit('validate', !this.selectedViews.filter(view => view.name === '').length)
      }
    }
  }
</script>

<style lang="scss">

</style>