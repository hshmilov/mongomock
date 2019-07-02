<template>
  <div class="x-select-views">
    <div
      v-for="(view, index) in value"
      :key="index"
      class="view"
    >
      <x-select-symbol
        :value="view.entity"
        :options="entities"
        type="icon"
        placeholder="Module..."
        @input="(entity) => updateEntity(index, entity)"
      />
      <x-select
        :value="view.name"
        :options="views[view.entity]"
        :searchable="true"
        placeholder="Query..."
        class="view-name"
        @input="(name) => updateName(index, name)"
      />
      <x-button
        v-if="index > 1"
        link
        @click="() => removeView(index)"
      >x</x-button>
      <div
        v-else
      />
    </div>
    <x-button
      light
      :disabled="hasMaxViews"
      :title="addBtnTitle"
      @click="addView"
    >+</x-button>
  </div>
</template>

<script>
  import xSelectSymbol from './SelectSymbol.vue'
  import xSelect from '../../axons/inputs/Select.vue'
  import xButton from '../../axons/inputs/Button.vue'

  const dashboardView = { name: '', entity: '' }
  export default {
    name: 'XSelectViews',
    components: {
      xSelectSymbol, xSelect, xButton
    },
    props: {
      value: {
        type: Array,
        default: () => []
      },
      entities: {
        type: Array,
        required: true
      },
      views: {
        type: Object,
        default: () => {}
      },
      max: {
        type: Number,
        default: 0
      }
    },
    computed: {
      selected: {
        get () {
          return this.value
        },
        set (selected) {
          this.$emit('input', selected)
        }
      },
      addBtnTitle() {
        return this.hasMaxViews? `Limited to ${this.max} queries` : ''
      },
      hasMaxViews() {
        if (!this.max || !this.selected) return false
        return this.selected.length === this.max
      }
    },
    methods: {
      updateName (index, name) {
        this.selected = this.selected.map((item, i) => {
          if (i === index) {
            item.name = name
          }
          return item
        })
      },
      updateEntity (index, entity) {
        this.selected = this.selected.map((item, i) => {
          if (i !== index) return item
          return {
            entity, name: ''
          }
        })
      },
      removeView (index) {
        this.selected = this.selected.filter((_, i) => i !== index)
      },
      addView () {
        this.selected = [...this.selected, { ...dashboardView }]
      }
    }
  }
</script>

<style lang="scss">
    .x-select-views {
      .view {
        display: grid;
        grid-template-columns: 160px auto 20px;
        grid-gap: 0 8px;
        min-width: 0;
        margin: 8px 0;
      }
    }

</style>