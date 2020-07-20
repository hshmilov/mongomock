import xTableData from '@axons/tables/TableData';
import { isObject, formatStringTemplate } from '@constants/utils';
import xSlice from '../schema/Slice.vue';

function processData(data, schema, sort) {
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

  return processedData;
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
  },
  render(createElement, { props }) {
    const {
      data, sort,
    } = props;
    const schema = { ...props.schema };
    const formatTitle = data ? data.formatTitle : undefined;
    if (schema.link) {
      schema.hyperlinks = () => ({
        href: formatStringTemplate(schema.link, data),
        type: 'link',
      });
    }
    const value = processData(data, schema, sort);
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
