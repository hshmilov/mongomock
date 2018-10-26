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
	notPattern: '({field} == exists(false) or {field} == type(10))'
}
const exists_str = {
	pattern: `(${exists.pattern} and {field} != '')`,
	notPattern: `(${exists.notPattern} or {field} == '')`
}
const exists_array = {
    pattern: `(${exists.pattern} and {field} != [])`,
    notPattern: `(${exists.notPattern} or {field} != [])`
}
const equals = {
	pattern: '{field} == "{val}"',
	notPattern: '{field} != "{val}"'
}
const contains = {
	pattern: '{field} == regex("{val}", "i")',
	notPattern: 'not {field} == regex("{val}", "i")'
}
const numerical = {
	'equals': {pattern: '{field} == {val}', notPattern: '{field} != {val}'},
	'<': {pattern: '{field} < {val}', notPattern: '{field} >= {val}'},
	'>': {pattern: '{field} > {val}', notPattern: '{field} <= {val}'},
	exists
}
const date = {
	'<': { pattern: '{field} < date("{val}")', notPattern: '{field} >= date("{val}")' },
	'>': { pattern: '{field} > date("{val}")', notPattern: '{field} <= date("{val}")' },
	'days': {
		pattern: '{field} >= date("NOW - {val}d")',
		notPattern: '{field} < date("NOW - {val}d")'
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
			notPattern: '({field}_raw < {val} or {field}_raw > {val})'
		},
		equals,
		'isIPv4': {
			pattern: '{field} == regex("\.")',
			notPattern: '{field} == regex("^(?!.*\.)")'
		},
		'isIPv6': {
			pattern: '{field} == regex(":")',
			notPattern: '{field} == regex("^(?!.*:)")'
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
			notPattern: '{field} == regex("^^(?!{val})", "i")'
		},
		'ends': {
			pattern: '{field} == regex("{val}$", "i")',
			notPattern: '{field} == regex("^(?!{val})$", "i")'
		},
        exists: exists_str
	},
	'bool': {
		'true': {pattern: '{field} == true', notPattern: '{field} == false'},
		'false': {pattern: '{field} == false', notPattern: '{field} == true'}
	},
	'percentage': numerical,
	'number': numerical,
	'integer': numerical
}
