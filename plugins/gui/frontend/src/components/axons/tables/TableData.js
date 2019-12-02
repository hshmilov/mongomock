import string from '../../neurons/schema/types/string/StringView.vue'
import number from '../../neurons/schema/types/numerical/NumberView.vue'
import integer from '../../neurons/schema/types/numerical/IntegerView.vue'
import bool from '../../neurons/schema/types/boolean/BooleanView.vue'
import file from '../../neurons/schema/types/array/FileView.vue'
import array from '../../neurons/schema/types/array/ArrayTableView.vue'
import xHyperlink from '../../neurons/schema/Hyperlink.vue'

import {isObject, isObjectListField} from '../../../constants/utils'

function processData(data, schema) {
  if (!schema.name || !isObject(data)) {
    return data
  }
  if (isObjectListField(schema)) {
    return Array.isArray(data)? data : [data]
  }
  return data[schema.name]
}

export default {
  functional: true,
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
  render(createElement, {props}) {
    const {schema, data} = props
    const value = processData(data, schema)
    const components = {string, number, integer, bool, file, array}
    const dataElement = createElement(components[Array.isArray(value)? 'array' : schema.type], {
      props: {
        schema,
        value
      }
    })
    if (schema.hyperlinks) {
      return createElement(xHyperlink, {
        props: schema.hyperlinks(value)
      }, [dataElement])
    }
    return dataElement
  }
}