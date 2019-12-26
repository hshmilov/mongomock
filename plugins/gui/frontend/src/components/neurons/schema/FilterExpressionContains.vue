<template>
  <div class="x-filter-expression-contains">
    <x-select
      v-model="fieldName"
      :options="options"
      placeholder="Field"
    />
    <input
      v-model="fieldValue"
      placeholder="Segment By..."
    >
    <x-button
      link
      @click="removeFilter"
    >x</x-button>
  </div>
</template>

<script>
    import xSelect from '../../axons/inputs/select/Select.vue'
    import xButton from '../../axons/inputs/Button.vue'

    export default {
        name: 'XFilterExpressionContains',
        components: {
            xSelect, xButton
        },
        props: {
            value: {
                type: Object,
                default: () => {}
            },
            options: {
                type: Array,
                default: () => []
            }
        },
        computed: {
            fieldName: {
                get () {
                    return this.value.name
                },
                set (name) {
                    this.updateFilter(name, 'name')
                }
            },
            fieldValue: {
                get () {
                    return this.value.value
                },
                set (value) {
                    this.updateFilter(value, 'value')
                }
            },
        },
        methods: {
            updateFilter (value, key) {
                const filter = {
                    ...this.value,
                    [key]: value
                }
                this.$emit('input', filter)
            },
            removeFilter () {
                this.$emit('remove-filter')
            }
        }
    }
</script>

<style lang="scss">
  .x-filter-expression-contains {
    display: grid;
    grid-template-columns: 160px auto 20px;
    grid-gap: 0 8px;
    min-width: 0;
    margin: 8px 0;
  }
</style>