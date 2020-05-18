import xTableData from '@axons/tables/TableData';
import { isObject, includesIgnoreCase, formatStringTemplate } from '@constants/utils';
import xSlice from '../schema/Slice.vue';

function passFilter(str, filter) {
  return includesIgnoreCase(str, filter.term) === filter.include;
}

function hasFilter(data, filters) {
  if (!data) return false;

  if (typeof data === 'string') {
    return filters.every((filter) => {
      return passFilter(data, filter);
    });
  }
  if (typeof data !== 'object') return false;

  const itemsToCheck = Array.isArray(data) ? data : Object.values(data).map((v) => v.toString());
  return filters.every((filter) => {
    if (filter.include) {
      return itemsToCheck.some((item) => passFilter(item, filter));
    }
    return itemsToCheck.every((item) => passFilter(item, filter));
  });
}

function processData(data, schema, filters, sort) {
  let processedData = data;
  if (schema.name && isObject(processedData)) {
    processedData = schema.rowDataTransform
      ? schema.rowDataTransform(processedData)
      : processedData[schema.name];
    if (Array.isArray(processedData) && sort && schema.name === sort.field) {
      processedData = [...processedData];
      processedData.sort();
      if (sort.desc) {
        processedData.reverse();
      }
    }
  }

  if (filters.length === 0) {
    return processedData;
  }

  if (Array.isArray(processedData)) {
    return processedData.filter((item) => hasFilter(item, filters));
  }
  return hasFilter(processedData, filters) ? processedData : null;
}

export default {
  functional: true,
  props: {
    schema: {
      type: Object,
      required: true,
    },
    data: {
      type: [String, Number, Boolean, Array, Object],
      default: undefined,
    },
    sort: {
      type: Object,
      default: () => ({
        field: '', desc: true,
      }),
    },
    filter: {
      type: Array,
      default: () => [],
    },
  },
  render(createElement, { props }) {
    const {
      data, filter, sort,
    } = props;
    const schema = { ...props.schema };
    const formatTitle = data ? data.formatTitle : undefined;
    if (schema.link) {
      schema.hyperlinks = () => ({
        href: formatStringTemplate(schema.link, data),
        type: 'link',
      });
    }
    const value = processData(data, schema, filter, sort);
    if (!Array.isArray(value)) {
      return createElement(xTableData, {
        props: {
          schema,
          data: value,
        },
      });
    }
    // Wrapping list data with a component limiting the items displayed,
    // with a tooltip presenting entire list
    return createElement(xSlice, {
      props: {
        schema,
        value,
      },
      scopedSlots: {
        default: ({ sliced }) => createElement(xTableData, {
          props: {
            schema,
            data: sliced,
            formatTitle,
          },
        }),
      },
    });
  },
};
