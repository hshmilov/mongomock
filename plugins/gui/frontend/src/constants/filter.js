export const childExpression = {
  expression: {
    field: '',
    compOp: '',
    value: null,
    filteredAdapters: null,
  },
  condition: '',
};

export const expression = {
  logicOp: '',
  not: false,
  leftBracket: false,
  field: '',
  compOp: '',
  value: null,
  rightBracket: false,
  children: [],
};

export const filterOutExpression = {
  logicOp: '',
  not: true,
  obj: false,
  leftBracket: false,
  field: 'internal_axon_id',
  fieldType: 'axonius',
  compOp: 'IN',
  rightBracket: false,
  children: [],
  showIds: false,
};

export const contextOptions = [
  { title: 'Aggregated Data', name: '' },
  { title: 'Complex Field', name: 'OBJ' },
  { title: 'Asset Entity', name: 'ENT' },
  { title: 'Field Comparison', name: 'CMP' },
];

export const logicOps = [
  { name: 'and', title: 'and' },
  { name: 'or', title: 'or' },
];

export const equalsFilter = [{
  name: 'equals',
  title: 'equals',
}];

export const dateFilter = [
  {
    name: 'equals',
    title: 'equals',
  },
  {
    name: '>',
    title: '>',
  },
  {
    name: '<',
    title: '<',
  },
  {
    name: '>Days',
    title: '> Days',
  },
  {
    name: '<Days',
    title: '< Days',
  },
];

export const INCLUDE_OUDATED_MAGIC = 'INCLUDE OUTDATED: ';

export const SIZE_OPERATOR = 'size';
export const SMALLER_THAN_OPERATOR = '<';
export const BIGGER_THAN_OPERATOR = '>';

export const osDistributionFormat = 'os-distribution';

const exists = '("{field}" == ({"$exists":true,"$ne":null}))';
const exists_str = '("{field}" == ({"$exists":true,"$ne":""}))';
const exists_array = '("{field}" == ({"$exists":true,"$ne":[]}))';
const equals = '"{field}" == "{val}"';
const IN = '"{field}" in [{val}]';
const contains = '"{field}" == regex("{val}", "i")';
const regex = '"{field}" == regex("{val}", "i")';
const numerical = {
  equals: '"{field}" == {val}',
  IN: '"{field}" in [{val}]',
  [SMALLER_THAN_OPERATOR]: '"{field}" < {val}',
  [BIGGER_THAN_OPERATOR]: '"{field}" > {val}',
  exists,
};
const date = {
  [SMALLER_THAN_OPERATOR]: '"{field}" < date("{val}")',
  [BIGGER_THAN_OPERATOR]: '"{field}" > date("{val}")',
  days: '"{field}" >= date("NOW {op} {val}d")',
  next_days: '"{field}" <= date("NOW {op} {val}d")',
  hours: '"{field}" >= date("NOW {op} {val}h")',
  next_hours: '"{field}" <= date("NOW {op} {val}h")',
  exists,
};

export const compOps = {
  array: {
    [SIZE_OPERATOR]: '"{field}" == size({val})',
    exists: exists_array,
  },
  array_discrete: {
    count_equals: '"{field}" == size({val})',
    count_below: '"{field}" < size({val})',
    count_above: '"{field}" > size({val})',
    exists: exists_array,
  },
  'date-time': date,
  date,
  time: { exists },
  ip: {
    subnet: '{val}',
    notInSubnet: '{val}',
    contains,
    equals,
    IN,
    regex,
    isIPv4: '"{field}" == regex("\\.")',
    isIPv6: '"{field}" == regex(":")',
    exists: exists_str,
  },
  ip_preferred: {
    contains,
    equals,
    IN,
    regex,
    isIPv4: '"{field}" == regex("\\.")',
    isIPv6: '"{field}" == regex(":")',
    exists: exists_str,
  },
  subnet: {
    contains,
    equals,
    IN,
    exists: exists_str,
  },
  version: {
    contains,
    equals,
    IN,
    regex,
    exists: exists_str,
    'earlier than': '"{field}_raw" < {val}',
    'later than': '"{field}_raw" > {val}',
  },
  tag: {
    contains,
    equals,
    IN,
    exists: 'tags == match([label_value != "" and label_value == exists(true)])',
  },
  image: {
    exists: exists_str,
  },
  string: {
    contains,
    equals,
    IN,
    starts: '"{field}" == regex("^{val}", "i")',
    ends: '"{field}" == regex("{val}$", "i")',
    regex,
    exists: exists_str,
  },
  bool: {
    true: '"{field}" == true',
    false: '"{field}" == false',
  },
  percentage: numerical,
  number: numerical,
  integer: numerical,
  [osDistributionFormat]: {
    contains,
    equals,
    IN,
    starts: '"{field}" == regex("^{val}", "i")',
    ends: '"{field}" == regex("{val}$", "i")',
    regex,
    [SMALLER_THAN_OPERATOR]: '"{field}" < "{val}"',
    [BIGGER_THAN_OPERATOR]: '"{field}" > "{val}"',
    exists: exists_str,
  },
};

export const opTitleTranslation = {
  count_equals: 'count =',
  count_below: 'count <',
  count_above: 'count >',
  notInSubnet: 'not in subnet',
  subnet: 'in subnet',
  days: 'last days',
  next_days: 'next days',
  hours: 'last hours',
  next_hours: 'next hours',
  sizegt: 'size >',
  sizelt: 'size <',
};

export const sizeLtGtFields = [
  'specific_data.data.associated_devices',
];

export const regexSpecialCharacters = /[-[\]{}()*+?.,\\^$|#]/g;

export const validateBrackets = (bracketWeights) => {
  let imbalance;
  const totalBrackets = bracketWeights.reduce((accumulator, currentVal) => {
    if (accumulator > 0) {
      imbalance = true;
    }
    return accumulator + currentVal;
  }, 0);

  if (imbalance) {
    return 'Missing left bracket';
  }
  if (totalBrackets !== 0) {
    return (totalBrackets < 0) ? 'Missing right bracket' : 'Missing left bracket';
  }
  return '';
};
