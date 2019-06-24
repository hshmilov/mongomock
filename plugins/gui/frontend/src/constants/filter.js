export const nestedExpression = {
    expression: {
        field: '',
        compOp: '',
        value: null
    }, condition: ''
}

export const expression = {
    logicOp: '',
    not: false,
    obj: false,
    leftBracket: false,
    field: '',
    compOp: '',
    value: null,
    rightBracket: false,
    nested: []
}

const exists = '({field} == ({"$exists":true,"$ne":null}))'
const exists_str = '({field} == ({"$exists":true,"$ne": ""}))'
const exists_array = '({field} == ({"$exists":true,"$ne":[]}))'
const equals = '{field} == "{val}"'
const contains = '{field} == regex("{val}", "i")'
const numerical = {
    equals: '{field} == {val}',
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
        'isIPv4': '{field} == regex("\\.")',
        'isIPv6': '{field} == regex(":")',
        exists: exists_str
    },
    subnet: {
        contains,
        equals,
        exists: exists_str
    },
    tag: {
        contains,
        equals,
        exists: 'tags == match([label_value != "" and label_value == exists(true)])'
    },
    image: {
        exists: exists_str
    },
    string: {
        contains,
        equals,
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
