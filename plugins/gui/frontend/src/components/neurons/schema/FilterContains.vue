<template>
  <div class="x-filter-contains">
    <x-filter-expression-contains
      v-for="(filter, index) in filters"
      :key="filter.index"
      :value="filters[index]"
      :options="options"
      @remove-filter="() => removeView(index)"
      @input="(newFilter) => updateFilter(newFilter, index)"
    />
    <x-button
      light
      :disabled="canAddFilters"
      @click="addFilter"
    >+</x-button>
  </div>
</template>

<script>
    import xButton from '../../axons/inputs/Button.vue'
    import XFilterExpressionContains from './FilterExpressionContains.vue'

    const fieldFilterEmpty = { name: '', value: '' }
    export default {
        name: 'XFilterContains',
        components: {
          xButton, XFilterExpressionContains
        },
        props: {
            value: {
                type: Array,
                default: () => []
            },
            options: {
                type: Array,
                default: () => []
            },
            min: {
                type: Number,
                default: 0
            }
        },
        computed: {
            filters: {
                get () {
                    return this.value
                },
                set (filters) {
                    this.$emit('input', filters)
                }
            },
            canAddFilters () {
              return !(this.filters.filter( item => !item.name || !item.value).length === 0)
            }
        },
        methods: {
            addFilter () {
              if(this.filters.filter( item => !item.name || !item.value).length === 0)
                  this.filters = [...this.filters,  {...fieldFilterEmpty} ]
            },
            isItemDeletable(index) {
                return index >= this.min
            },
            removeView (index) {
              if(index >= this.min)
                this.filters = this.filters.filter((_, i) => i !== index)
              else {
                this.filters = this.filters.map((item, i) => {
                  if (i === index) {
                    return {...fieldFilterEmpty}
                  }
                  return item
                })
              }
            },
            updateFilter(filter, index) {
              this.filters = this.filters.map((item, i) => {
                if (i === index) {
                  return filter
                }
                return item
              })
            }
        }
    }
</script>

<style lang="scss">

</style>