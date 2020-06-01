import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import utc from 'dayjs/plugin/utc';
import { DEFAULT_DATE_FORMAT } from '../store/modules/constants';
import { ChartTypesEnum } from './dashboard'

dayjs.extend(isoWeek);
dayjs.extend(utc);

export const formatDate = (dateString, schema, dateFormat) => {
  if (!dayjs(dateString).isValid()) {
    return dateString;
  }
  if (dateFormat === undefined) {
    dateFormat = DEFAULT_DATE_FORMAT;
  }
  const dateTime = dayjs(dateString);
  if (schema && schema.format === 'date') {
    return dateTime.format(dateFormat);
  }
  if (schema && schema.format === 'time') {
    return dateTime.format('HH:mm:ss');
  }
  return dateTime.format(`${dateFormat} HH:mm:ss`);
};

export const includesIgnoreCase = (str, substring) => (
  str && str.toLowerCase().includes(substring.toLowerCase())
);

export const calcMaxIndex = (list) => (list.length > 0
  ? Math.max(...list.map((item) => item.i || 0)) + 1 : 0);

export const isObjectListField = (field) => field.items !== undefined && !Array.isArray(field.items) && field.items.type === 'array';

export const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);

export const getExcludedAdaptersFilter = (fieldType, field, filteredAdapters, condition) => {
  let excludedAdapters = '';
  let resultCondition = condition;
  if (fieldType === 'axonius'
        && filteredAdapters
        && field.indexOf('specific_data.data') !== -1
        && !filteredAdapters.selectAll
        && !filteredAdapters.clearAll) {
    resultCondition = condition.replace('specific_data.data.', 'data.');
    excludedAdapters = Object.keys(filteredAdapters.selectedValues).filter((key) => !filteredAdapters.selectedValues[key]).join("', '");
  } else {
    return resultCondition;
  }
  return `specific_data == match([plugin_name not in ['${excludedAdapters}'] and ${resultCondition}])`;
};

export const getTypeFromField = (fieldName) => {
  /*
    Parse a field path to extract the prefix that indicates which Adapter it is from.
    If no such prefix, return the general field type
     */
  const fieldSpaceMatch = /adapters_data\.(\w+)\./.exec(fieldName);
  if (fieldSpaceMatch && fieldSpaceMatch.length > 1) {
    return fieldSpaceMatch[1];
  }
  return 'axonius';
};


export const formatStringTemplate = (str, data = {}) => {
  /*
    Format a string template
    str - the string template with '{{<parameter>}}' placeholders
    data - the parameters map
     */
  let result = str;
  Object.keys(data).forEach((key) => {
    result = result.replace(new RegExp(`{{${key}}}`, 'g'), data[key]);
  });
  return result;
};

const createWeekDayObject = (item) => ({
  name: item,
  title: dayjs().isoWeekday(item + 1).format('dddd'),
});

const createMonthDayObject = (item) => {
  const day = item + 1;
  let title = day.toString();
  if (day === 29) {
    title = 'Last Day';
  }
  return { name: day, title };
};

export const weekDays = Array.from(new Array(7).keys()).map(createWeekDayObject);

export const monthDays = Array.from(new Array(29).keys()).map(createMonthDayObject);

export const parseVaultError = (errorString) => {
  const regexp = '.*_vault_error\\:(.+?)\\:(.*)';
  const errorParts = errorString.match(regexp) || [];
  const [, field, exception] = errorParts;
  const error = exception || errorString;
  return {
    error, field,
  };
};

export const getParentFromField = (fieldName) => fieldName.split('.').slice(0, -1).join('.');

export const validateClassName = (name) => /^([a-z_]|-[a-z_-])[a-z\d_-]*$/i.test(name);

// Gets the chart views according to its metric type
export const ChartViewGetter = (chart) => {

  // The key for each getter is the chart metric
  const getters = {
    [ChartTypesEnum.intersect]: (config) => {
      return config.intersecting.concat(config.base).map((view) => {
        return {
          id: view,
          entity: config.entity,
        }
      });
    },
    [ChartTypesEnum.compare]: (config) => {
      return config.views;
    },
    [ChartTypesEnum.segment]: (config) => {
      return [{ id: config.view, entity: config.entity}];
    },
    [ChartTypesEnum.abstract]: (config) => {
      return [{ id: config.view, entity: config.entity}];
    },
    [ChartTypesEnum.timeline]: (config) => {
      return config.views;
    },
    [ChartTypesEnum.matrix]: (config) => {
      return config.intersecting.concat(config.base).map((view) => {
        return {
          id: view,
          entity: config.entity,
        }
      });
    },
  }

  return getters[chart.metric](chart.config);
};
