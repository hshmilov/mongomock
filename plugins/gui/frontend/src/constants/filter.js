export const childExpression = {
    expression: {
        field: '',
        compOp: '',
        value: null,
        filteredAdapters: null
    },
    condition: ''
}

export const expression = {
    logicOp: '',
    not: false,
    leftBracket: false,
    field: '',
    compOp: '',
    value: null,
    rightBracket: false,
    children: []
}

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
    showIds: false
}

export const INCLUDE_OUDATED_MAGIC = 'INCLUDE OUTDATED: '

const exists = '({field} == ({"$exists":true,"$ne":null}))'
const exists_str = '({field} == ({"$exists":true,"$ne":""}))'
const exists_array = '({field} == ({"$exists":true,"$ne":[]}))'
const equals = '{field} == "{val}"'
const IN = '{field} in [{val}]'
const contains = '{field} == regex("{val}", "i")'
const numerical = {
    equals: '{field} == {val}',
    IN: '{field} in [{val}]',
    '<': '{field} < {val}',
    '>': '{field} > {val}',
    exists
}
const date = {
    '<': '{field} < date("{val}")',
    '>': '{field} > date("{val}")',
    days: '{field} >= date("NOW - {val}d")',
    exists
}
export const compOps = {
    array: {
        size: '{field} == size({val})',
        exists: exists_array
    },
    array_discrete: {
        count_equals: '{field} == size({val})',
        count_below: '{field} < size({val})',
        count_above: '{field} > size({val})',
        exists: exists_array
    },
    'date-time': date,
    date,
    time: {exists},
    ip: {
        subnet: '{field}_raw == match({"$gte": {val}, "$lte": {val}})',
        notInSubnet: '{val}',
        contains,
        equals,
        IN,
        'isIPv4': '{field} == regex("\\.")',
        'isIPv6': '{field} == regex(":")',
        exists: exists_str
    },
    subnet: {
        contains,
        equals,
        IN,
        exists: exists_str
    },
    version: {
        contains,
        equals,
        IN,
        exists: exists_str,
        'earlier than': '{field}_raw < {val}',
        'later than': '{field}_raw > {val}'
    },
    tag: {
        contains,
        equals,
        IN,
        exists: 'tags == match([label_value != "" and label_value == exists(true)])'
    },
    image: {
        exists: exists_str
    },
    string: {
        contains,
        equals,
        IN,
        starts: '{field} == regex("^{val}", "i")',
        ends: '{field} == regex("{val}$", "i")',
        exists: exists_str
    },
    bool: {
        true: '{field} == true',
        false: '{field} == false'
    },
    percentage: numerical,
    number: numerical,
    integer: numerical
}

export const opTitleTranslation = {
    count_equals: 'count =',
    count_below: 'count <',
    count_above: 'count >',
    notInSubnet: 'not in subnet',
    subnet: 'in subnet'
}
