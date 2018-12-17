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

const exists = '({field} == exists(true) and not {field} == type(10))'
const exists_str = `(${exists} and {field} != '')`
const exists_array = `(${exists} and {field} != [])`
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
    'date-time': date,
    date,
    time: {exists},
    ip: {
        subnet: '{field}_raw == match({"$gte": {val}, "$lte": {val}})',
        equals,
        'isIPv4': '{field} == regex("\\.")',
        'isIPv6': '{field} == regex(":")',
        exists: exists_str
    },
    'tag': {
        contains,
        equals,
        exists: exists_str
    },
    'image': {
        exists: exists_str
    },
    'string': {
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
