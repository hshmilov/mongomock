import _isEmpty from 'lodash/isEmpty';
import _isEqual from 'lodash/isEqual';
import IP from 'ip';

import { getExcludedAdaptersFilter } from '../constants/utils';
import {
  compOps, opTitleTranslation, sizeLtGtFields, regexSpecialCharacters, osDistributionFormat,
  SMALLER_THAN_OPERATOR, BIGGER_THAN_OPERATOR,
} from '../constants/filter';
import { pluginTitlesToNames } from '../constants/plugin_meta';

const convertSubnetToRaw = (val) => {
  if (!val.includes('/') || val.indexOf('/') === val.length - 1) {
    return [];
  }
  try {
    const subnetInfo = IP.cidrSubnet(val);
    return [IP.toLong(subnetInfo.networkAddress), IP.toLong(subnetInfo.broadcastAddress)];
  } catch (err) {
    return [];
  }
};

/**
 * A module that calculates a single condition in an expression
 * @param {string} field - the field of the condition
 * @param {object} fieldSchema - the schema of the field
 * @param {string} adapter - the adapter this field belongs to
 * @param {string} compOp - the compare operator (equals, contains...)
 * @param {string} value - the value of the condition
 * @param {array} filteredAdapters - the filtered out adapters (if there are any)
 * @return {{formatCondition: function, composeCondition: function}}
 * @constructor
 */
const Condition = function (field, fieldSchema, adapter, compOp, value, filteredAdapters, not) {
  const operator = getOpsMap(fieldSchema)[compOp];
  let processedValue = '';

  const formatNotInSubnet = () => {
    const subnets = value.split(',');
    const rawIpsArray = [];
    let result = [[0, 0xffffffff]];
    for (let i = 0; i < subnets.length; i++) {
      const subnet = subnets[i].trim();
      if (subnet !== '') {
        const rawIps = convertSubnetToRaw(subnet);
        if (rawIps.length === 0) {
          return `Invalid "${subnet}", Specify <address>/<CIDR>`;
        }
        rawIpsArray.push(rawIps);
      }
    }
    rawIpsArray.sort((range1, range2) => (range1[0] - range2[0]));
    rawIpsArray.forEach((range) => {
      const lastRange = result.pop(-1);
      result.push([lastRange[0], range[0]]);
      result.push([range[1], lastRange[1]]);
    });
    result = result
      .map((range) => (`"${field}_raw" == match({"$gte": ${range[0]}, "$lte": ${range[1]}})`))
      .join(' or ');
    processedValue = `(${result})`;
    return '';
  };

  const formatInSubnet = () => {
    const subnets = value.split(',');
    const rawIpsArray = [];
    for (let i = 0; i < subnets.length; i++) {
      const subnet = subnets[i].trim();
      if (subnet !== '') {
        const rawIps = convertSubnetToRaw(subnet);
        if (rawIps.length === 0) {
          return 'Specify <address>/<CIDR> to filter IP by subnet';
        }
        rawIpsArray.push(rawIps);
      }
    }
    const result = rawIpsArray
      .map((range) => (`"${field}_raw" == match({"$gte": ${range[0]}, "$lte": ${range[1]}})`))
      .join(' or ');
    processedValue = `(${result})`;
    return '';
  };

  const formatVersion = () => {
    const rawVersion = convertVersionToRaw(value);
    if (rawVersion.length === 0) {
      return 'Invalid version format, must be <optional>:<period>.<separated>.<numbers>';
    }
    processedValue = `'${rawVersion}'`;
    return '';
  };

  const formatIn = () => {
    if (!value) {
      return '';
    }
    let values = value.match(/(\\,|[^,])+/g);
    if (field === 'adapters') {
      values = values.map((adapter) => pluginTitlesToNames[adapter.trim()]).filter((value) => value);
    }
    if (['integer', 'number'].includes(fieldSchema.type)) {
      processedValue = values.map((value) => parseFloat(value)).filter((value) => !isNaN(value)).join(',');
      if (!processedValue) return 'Only numbers allowed in this filter';
    } else {
      processedValue = `"${values.join('","')}"`;
    }
    processedValue = processedValue.replace('\\\\,', ',');
    return '';
  };

  const getConditionExpression = () => {
    let cond = '({val})';
    if (operator) {
      cond = operator.replace(/{field}/g, field);
    }
    let val = processedValue || value;
    let iVal = Array.isArray(val) ? -1 : undefined;
    if (compOp === 'days' || compOp === 'hours') {
      const op = val < 0 ? '+' : '-';
      val = Math.abs(val);
      cond = cond.replace(/{op}/g, op);
    } else if (compOp === 'next_days' || compOp === 'next_hours') {
      const op = val < 0 ? '-' : '+';
      val = Math.abs(val);
      cond = cond.replace(/{op}/g, op);
    }
    else if (compOp === 'contains') {
      // escape regex special characters.
      val = val.replace(regexSpecialCharacters, '\\$&');
    }
    cond = cond.replace(/{val}/g, () => {
      if (iVal === undefined) return val;
      iVal = (iVal + 1) % val.length;
      return val[iVal];
    });
    return not ? `not (${cond})` : cond;
  };

  /**
   * Format the condition value before the compilation
   * @returns {string} - the first error if there is at least one
   */
  const formatCondition = () => {
    processedValue = '';
    if (compOp === 'IN') {
      return formatIn();
    }
    if (!fieldSchema) {
      return '';
    }
    if (fieldSchema.format && fieldSchema.format === 'ip') {
      if (compOp === 'subnet') {
        return formatInSubnet();
      }
      if (compOp === 'notInSubnet') {
        return formatNotInSubnet();
      }
    }

    if (fieldSchema.format && fieldSchema.format === 'version') {
      if (compOp === 'earlier than' || compOp === 'later than') {
        return formatVersion();
      }
    }

    if (fieldSchema.format && fieldSchema.format === osDistributionFormat) {
      if (compOp !== SMALLER_THAN_OPERATOR && compOp !== BIGGER_THAN_OPERATOR) {
        return '';
      }
    }

    const valueSchema = getValueSchema(fieldSchema, compOp);
    if (value && !_isEmpty(valueSchema.enum)) {
      if (compOp === 'equals' && !schemaEnumFind(valueSchema, value)) {
        return 'Specify a valid value for enum field';
      }
    }
    return '';
  };

  /**
   * Compose/Compile the condition into string condition
   * @returns {string} - the string condition
   */
  const composeCondition = () => {
    if (!field) return '';

    const error = getError(field, fieldSchema, compOp, value);
    if (error) {
      throw error;
    }
    return `(${getExcludedAdaptersFilter(adapter, field,
      filteredAdapters, getConditionExpression())})`;
  };

  return {
    formatCondition,
    composeCondition,
  };
};

export const schemaEnumFind = (schema, value) => schema.enum.find((item, index) => {
  if (schema.type === 'integer' && isNaN(item)) {
    return index + 1 === value;
  }
  return (item.name || item) === value;
});

const extendVersionField = (val) => {
  let extended = '';
  for (let i = 0; i < 8 - val.length; i++) {
    extended = `0${extended}`;
  }
  extended += val;
  return extended;
};

const convertVersionToRaw = (version) => {
  try {
    let converted = '0';
    if (version.includes(':')) {
      if (version.includes('.') && version.indexOf(':') > version.indexOf('.')) {
        return '';
      }
      const epoch_split = version.split(':');
      converted = epoch_split[0];
      version = epoch_split[1];
    }
    let split_version = [version];
    if (version.includes('.')) {
      split_version = version.split('.');
    }
    for (let i = 0; i < split_version.length; i++) {
      if (isNaN(split_version[i])) {
        return '';
      }
      if (split_version[i].length > 8) {
        split_version[i] = split_version[i].substring(0, 9);
      }
      const extended = extendVersionField(split_version[i]);
      converted += extended;
    }
    return converted;
  } catch (err) {
    return '';
  }
};

/**
 * Check if the condition is not valid
 * @param {string} field - the field of the condition
 * @param {object} fieldSchema - the schema of the field
 * @param {string} compOp - the compare operator (equals, contains...)
 * @param {string} value - the value of the condition
 * @returns {string}
 */
export const getError = (field, fieldSchema, compOp, value) => {
  if (!field) {
    return '';
  }
  const opsMap = getOpsMap(fieldSchema);
  if (getOpsList(opsMap).length && (!compOp || !opsMap[compOp])) {
    return 'Comparison operator is needed to add expression to the filter';
  } if (checkShowValue(fieldSchema, compOp) && (typeof value !== 'number' || isNaN(value))
    && (!value || !value.length)) {
    return 'A value to compare is needed to add expression to the filter';
  }
  return '';
};

/**
 * Checks if this condition uses the value attribute
 * @param {object} fieldSchema - the schema of the field
 * @param {string} compOp - the compare operator (equals, contains...)
 * @returns {*|boolean|number}
 */
export const checkShowValue = (fieldSchema, compOp) => {
  const opsMap = getOpsMap(fieldSchema);
  return (fieldSchema && (fieldSchema.format === 'predefined'
    || (compOp && getOpsList(opsMap).length && opsMap[compOp] && opsMap[compOp].includes('{val}'))))
    || !fieldSchema;
};

/**
 * Get the operator map
 * @param {object} schema - the schema of the current page
 * @returns {{}} - a map of the operators available
 */
export const getOpsMap = (schema) => {
  if (!schema || !schema) return {};
  let ops = {};
  const parentSchema = schema;
  if (schema.type === 'array') {
    ops = compOps[`array_${schema.format}`] || compOps.array;
    if (sizeLtGtFields.includes(schema.name)) {
      ops.sizegt = '{val}';
      ops.sizelt = '{val}';
    }
    schema = schema.items;
  }
  const specialEnumFormats = new Set(['predefined', 'tag', osDistributionFormat]);
  if (schema.enum && !specialEnumFormats.has(schema.format)) {
    ops = {
      ...ops,
      equals: compOps[schema.type].equals,
      exists: compOps[schema.type].exists,
      IN: compOps[schema.type].IN,
    };
  } else if (schema.format) {
    ops = { ...ops, ...compOps[schema.format] };
  } else {
    ops = { ...ops, ...compOps[schema.type] };
  }
  if (parentSchema.type === 'array') {
    ops.exists = compOps[parentSchema.type].exists;
  }
  if (schema.type === 'array' && ops.exists) {
    ops.exists = `(${ops.exists} and "{field}" != [])`;
  }
  if (schema.name === 'labels') {
    delete ops.size;
  }
  return ops;
};

/**
 * Get the operator list for display
 * @param {object} opsMap - the operator map of the current schema
 * @returns {{name: string, title: string}[]} - a operator list for display
 */
export const getOpsList = (opsMap) => Object.keys(opsMap).map((op) => ({
  name: op,
  title: opTitleTranslation[op] ? opTitleTranslation[op].toLowerCase() : op.toLowerCase(),
}));

const isStringComparison = (schema, compOp) => {
  const typesExpectingString = ['string', 'integer', 'number', 'array'];
  const opsExpectingString = ['IN', 'contains', 'regex'];
  return typesExpectingString.includes(schema.type) && opsExpectingString.includes(compOp);
};

const isOsDistributionStringComparison = (schema, compOp) => {
  const typesExpectingString = ['string'];
  const opsExpectingString = ['equals', 'starts', 'ends'];
  return (schema.format === osDistributionFormat) && typesExpectingString.includes(schema.type)
      && opsExpectingString.includes(compOp);
};

const isArrayItemsComparison = (schema, compOp) => {
  const typesExpectingItems = ['array'];
  const opsExpectingItems = ['contains', 'equals', 'subnet', 'notInSubnet', 'starts', 'ends'];
  return typesExpectingItems.includes(schema.type) && opsExpectingItems.includes(compOp);
};

const isDateCountComparison = (schema, compOp) => {
  const opsExpectingInteger = ['days', 'next_days', 'hours', 'next_hours'];
  const isSchemaDate = schema.format && schema.format === 'date-time';
  return isSchemaDate && opsExpectingInteger.includes(compOp);
};

const isNaturalIntComparison = (schema) => ['number', 'integer', 'array'].includes(schema.type);

export const getValueSchema = (fieldSchema, compOp) => {
  if (!fieldSchema) {
    return {};
  }
  if (isStringComparison(fieldSchema, compOp)) {
    return { type: 'string' };
  }
  if (isOsDistributionStringComparison(fieldSchema, compOp)) {
    return { type: 'string' };
  }
  if (isDateCountComparison(fieldSchema, compOp)) {
    return {
      type: 'integer',
      allow_negatives: true,
    };
  }
  const finalSchema = isArrayItemsComparison(fieldSchema, compOp) ? fieldSchema.items : fieldSchema
  return isNaturalIntComparison(finalSchema) ? { ...finalSchema, min: 0 } : finalSchema;
};

export const getUpdatedValueAfterFieldChange = (
  newFieldSchema, prevFieldSchema, compOp, prevValue,
) => {
  let value = prevValue;
  // Reset the value if the value schema is about to change
  if (!_isEqual(getValueSchema(newFieldSchema, compOp),
    getValueSchema(prevFieldSchema, compOp))) {
    value = '';
  }
  return value;
};

export default Condition;
