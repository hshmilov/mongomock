<template>
  <component
    :is="schema.type"
    :schema="schema"
    :value="value"
  />
</template>

<script>
  import string from '../../neurons/schema/types/string/StringView.vue'
  import number from '../../neurons/schema/types/numerical/NumberView.vue'
  import integer from '../../neurons/schema/types/numerical/IntegerView.vue'
  import bool from '../../neurons/schema/types/boolean/BooleanView.vue'
  import file from '../../neurons/schema/types/array/FileView.vue'
  import array from '../../neurons/schema/types/array/ArrayTableView.vue'

  export default {
    name: 'XTableData',
    components: {
      string, integer, number, bool, file, array
    },
    props: {
      schema: {
        type: Object,
        required: true
      },
      data: {
        type: [String, Number, Boolean, Array, Object],
        default: undefined
      },
      sort: {
        type: Object,
        default: () => {
          return {
            field: '', desc: true
          }
        }
      }
    },
    computed: {
      fieldName() {
        return this.schema.name
      },
      isObject() {
        return this.data && typeof this.data === 'object' && !Array.isArray(this.data)
      },
      value () {
        if (!this.fieldName || !this.isObject) return this.data
        let value = this.data[this.fieldName]
        if (Array.isArray(value) && this.sort && this.fieldName === this.sort.field && !this.sort.desc) {
          return [...value].reverse()
        }
        return value
      }
    }
  }
</script>

<style lang="scss">

</style>