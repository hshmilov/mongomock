<template>
  <component
    :is="dataType"
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

  import {isObject, isObjectListField} from '../../../constants/utils'

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
      }
    },
    computed: {
      dataType () {
        if (this.schema.type !== 'array' && Array.isArray(this.data)) {
          return 'array'
        }
        return this.schema.type
      },
      value () {
        if (!this.schema.name || !isObject(this.data)) {
          return this.data
        }
        if (isObjectListField(this.schema)) {
          return Array.isArray(this.data)? this.data : [this.data]
        }
        return this.data[this.schema.name]
      }
    }
  }
</script>

<style lang="scss">

</style>