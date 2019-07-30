<template>
  <div class="x-chart-metric">
    <label>Module for chart:</label>
    <x-select-symbol
      id="module"
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      class="grid-span2"
      @input="updateEntity"
    />

    <label>Base Query:</label>
    <x-select
      id="baseQuery"
      v-model="base"
      :options="views[entity]"
      :searchable="true"
      placeholder="query (or empty for all)"
      class="grid-span2 view-name"
    />

    <label>Intersecting Query:</label>
    <x-select
      id="intersectingFirst"
      :value="intersecting[0]"
      :options="views[entity]"
      :searchable="true"
      placeholder="query..."
      class="grid-span2"
      @input="(view) => updateIntersecting(0, view)"
    />
    <template v-if="intersecting.length > 1">
      <label>Intersecting Query:</label>
      <x-select
        id="intersectingSecond"
        :value="intersecting[1]"
        :options="views[entity]"
        :searchable="true"
        placeholder="query..."
        @input="(view) => updateIntersecting(1, view)"
      />
      <x-button
        link
        @click="removeIntersecting(1)"
      >x</x-button>
    </template>
    <x-button
      light
      :disabled="hasMaxViews"
      class="grid-span3"
      :title="addBtnTitle"
      @click="addIntersecting"
    >+</x-button>
  </div>
</template>

<script>
  import xButton from '../../../axons/inputs/Button.vue'
  import xSelect from '../../../axons/inputs/Select.vue'
  import xSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue'
  import chartMixin from './chart'

  export default {
    name: 'XChartIntersect',
    components: { xButton, xSelect, xSelectSymbol },
    mixins: [chartMixin],
    data () {
      return {
        max: 2
      }
    },
    computed: {
      initConfig () {
        return {
          entity: '', base: '', intersecting: ['', '']
        }
      },
      entity: {
        get () {
          return this.config.entity
        },
        set (entity) {
          this.config = { ...this.config, entity}
        }
      },
      base: {
        get () {
          return this.config.base
        },
        set (base) {
          this.config = { ...this.config, base }
        }
      },
      intersecting: {
        get () {
          return this.config.intersecting
        },
        set (intersecting) {
          this.config = { ...this.config, intersecting: [...intersecting]}
        }
      },
      hasMaxViews () {
        if (!this.max) return false
        return this.intersecting.length === this.max
      },
      addBtnTitle() {
        return this.hasMaxViews? `Limited to ${this.max} intersecting queries` : ''
      },
    },
    methods: {
      updateEntity (entity) {
        if (entity === this.entity) return
        this.config = {
          entity,
          base: '',
          intersecting: ['', '']
        }
        this.$emit('state')
      },
      removeIntersecting (index) {
        this.intersecting.splice(index, 1)
        this.intersecting = [...this.intersecting]
      },
      addIntersecting () {
        this.intersecting = [...this.intersecting, '']
      },
      updateIntersecting(index, view) {
        this.intersecting = this.intersecting.map((item, ind) => {
          if (ind === index) return view
          return item
        })
        this.$emit('state')
      },
      validate () {
        this.$emit('validate', !this.intersecting.filter(view => view === '').length)
      }
    }
  }
</script>

<style lang="scss">

</style>