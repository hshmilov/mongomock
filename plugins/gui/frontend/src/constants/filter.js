export const expression =  {
	logicOp: '',
	not: false,
	leftBracket: false,
	field: '',
	compOp: '',
	value: null,
	rightBracket: false
}

const exists = {
	pattern: '({field} == exists(true) and not {field} == type(10))',
	notPattern: '(not ({field} == exists(true) and not {field} == type(10)))'
}
const exists_str = {
	pattern: `(${exists.pattern} and {field} != '')`,
	notPattern: `(not (${exists.pattern} and {field} != ''))`
}
const exists_array = {
    pattern: `(${exists.pattern} and {field} != [])`,
    notPattern: `(not (${exists.pattern} and {field} != []))`
}
const equals = {
	pattern: '{field} == "{val}"',
	notPattern: '(not ({field} == "{val}"))'
}
const contains = {
	pattern: '{field} == regex("{val}", "i")',
	notPattern: 'not {field} == regex("{val}", "i")'
}
const numerical = {
	'equals': {pattern: '{field} == {val}', notPattern: 'not {field} == {val}'},
	'<': {pattern: '{field} < {val}', notPattern: 'not {field} < {val}'},
	'>': {pattern: '{field} > {val}', notPattern: 'not {field} > {val}'},
	exists
}
const date = {
	'<': { pattern: '{field} < date("{val}")', notPattern: 'not {field} < date("{val}")' },
	'>': { pattern: '{field} > date("{val}")', notPattern: 'not {field} > date("{val}")' },
	'days': {
		pattern: '{field} >= date("NOW - {val}d")',
		notPattern: 'not {field} >= date("NOW - {val}d")'
	},
	exists
}
export const compOps = {
	'array': {
		'size': {
			pattern: '{field} == size({val})',
			notPattern: 'not {field} == size({val})'
		},
		exists: exists_array
	},
	'date-time': {
		...date
	},
	'date': {
		...date
	},
	'time': {
		exists
	},
	'ip': {
		'subnet': {
			pattern: '{field}_raw == match({"$gte": {val}, "$lte": {val}})',
			notPattern: 'not ({field}_raw == match({"$gte": {val}, "$lte": {val}}))'
		},
		equals,
		'isIPv4': {
			pattern: '{field} == regex("\.")',
			notPattern: 'not ({field} == regex("."))'
		},
		'isIPv6': {
			pattern: '{field} == regex(":")',
			notPattern: 'not ({field} == regex(":"))'
		},
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
		'starts': {
			pattern: '{field} == regex("^{val}", "i")',
			notPattern: 'not ({field} == regex("^{val}", "i"))'
		},
		'ends': {
			pattern: '{field} == regex("{val}$", "i")',
			notPattern: 'not ({field} == regex("{val}$", "i"))'
		},
        exists: exists_str
	},
	'bool': {
		'true': {pattern: '{field} == true', notPattern: 'not ({field} == true)'},
		'false': {pattern: '{field} == false', notPattern: 'not ({field} == false)'}
	},
	'percentage': numerical,
	'number': numerical,
	'integer': numerical
}
