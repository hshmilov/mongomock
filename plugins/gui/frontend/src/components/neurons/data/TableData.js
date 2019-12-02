import xSlice from '../schema/Slice.vue'
import xTableData from '../../axons/tables/TableData.js'

import {isObject, includesIgnoreCase, formatStringTemplate} from '../../../constants/utils'

function hasFilter(data, filter) {
  if (!data) {
    return false
  }
  if (typeof data === 'string') {
    return includesIgnoreCase(data, filter)
  }
  if (typeof data !== 'object') {
    return false
  }
  const itemsToCheck = Array.isArray(data) ? data : Object.values(data)
  return Boolean(itemsToCheck.find(item => hasFilter(item, filter)))
}

function processData(data, schema, filter, sort) {
  if (schema.name && isObject(data)) {
    data = data[schema.name]
    if (Array.isArray(data) && sort && schema.name === sort.field) {
      data = [...data]
      data.sort()
      if (sort.desc) {
        data.reverse()
      }
    }
  }
  if (!filter) {
    return data
  }
  if (Array.isArray(data)) {
    return data.filter(item => hasFilter(item, filter))
  }
  return hasFilter(data, filter) ? data : null
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
    },
    sort: {
      type: Object,
      default: () => {
        return {
          field: '', desc: true
        }
      }
    },
    filter: {
      type: String,
      default: ''
    }
  },
  render(createElement, {props}) {
    let {data, schema, filter, sort} = props
    schema = {...schema}
    if (schema.link) {
      schema.hyperlinks = () => {
        return {
          href: formatStringTemplate(schema.link, data),
          type: 'link'
        }
      }
    }
    const value = processData(data, schema, filter, sort)
    if (!Array.isArray(value)) {
      return createElement(xTableData, {
        props: {
          schema,
          data: value
        }
      })
    }
    // Wrapping list data with a component limiting the items displayed, with a tooltip presenting entire list
    return createElement(xSlice, {
      props: {
        schema,
        value
      },
      scopedSlots: {
        default: ({ sliced }) => createElement(xTableData, {
          props: {
            schema,
            data: sliced
          }
        })
      }
    })
  }
}