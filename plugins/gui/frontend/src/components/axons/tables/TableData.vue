<template>
  <component
    :is="dataType"
    :schema="schema"
    :value="value"
    :link="link"
  />
</template>

<script>
  import string from '../../neurons/schema/types/string/StringView.vue'
  import number from '../../neurons/schema/types/numerical/NumberView.vue'
  import integer from '../../neurons/schema/types/numerical/IntegerView.vue'
  import bool from '../../neurons/schema/types/boolean/BooleanView.vue'
  import file from '../../neurons/schema/types/array/FileView.vue'
  import array from '../../neurons/schema/types/array/ArrayTableView.vue'
  import {formatStringTemplate} from '../../../constants/utils.js'

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
        let value = this.data[this.schema.name]
        if (value === undefined) {
          value = this.data
        }
        return (isObjectListField(this.schema) && !Array.isArray(value)) ? [value] : value
      },
      link () {
          if(this.schema.link){
              return formatStringTemplate(this.schema.link, this.data)
          }
          return ''
      }
    }
  }
</script>

<style lang="scss">

</style>