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
	pattern: '({field} == exists(true) and {field} != "")',
	notPattern: '({field} == exists(false) or {field} == "")'
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
	'>': {pattern: '{field} > {val}', notPattern: '{field} <= {val}'}
}
const date = {
	'<': { pattern: '{field} < date("{val}")', notPattern: '{field} >= date("{val}")' },
	'>': { pattern: '{field} > date("{val}")', notPattern: '{field} <= date("{val}")' },
	'days': {
		pattern: '{field} >= date("NOW - {val}d")',
		notPattern: '{field} < date("NOW - {val}d")'
	}
}
export const compOps = {
	'array': {
		'size': {
			pattern: '{field} == size({val})',
			notPattern: 'not {field} == size({val})'
		},
		'exists': {
			pattern: '({field} == exists(true) and {field} > [])',
			notPattern: '({field} == exists(false) or {field} == [])'
		}
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
		exists
	},
	'tag': {
		contains,
		equals
	},
	'image': {
		exists
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
		exists
	},
	'bool': {
		'true': {pattern: '{field} == true', notPattern: '{field} == false'},
		'false': {pattern: '{field} == false', notPattern: '{field} == true'}
	},
	'percentage': numerical,
	'number': numerical,
	'integer': numerical
}
