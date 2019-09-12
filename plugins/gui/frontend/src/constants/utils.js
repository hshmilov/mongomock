export const formatDate = (dateString, schema) => {
    let dateTime = new Date(dateString);
    if (dateTime == 'Invalid Date') return value
    dateTime.setMinutes(dateTime.getMinutes() - dateTime.getTimezoneOffset())
    let dateParts = dateTime.toISOString().split('T')
    dateParts[1] = dateParts[1].split('.')[0]
    if (schema && schema.format === 'date') {
        return dateParts[0]
    }
    if (schema && schema.format === 'time') {
        return dateParts[1]
    }
    return dateParts.join(' ')
}

export const includesIgnoreCase = (str, substring) => {
    return str && str.toLowerCase().includes(substring)
}

export const calcMaxIndex = (list) => {
    return list.length > 0 ? Math.max(...list.map(item => item.i)) + 1 : 0
}

export const isObjectListField = (field) => {
    return field.items !== undefined && !Array.isArray(field.items) && field.items.type === 'array'
}

export const getExcludedAdaptersFilter = (fieldType, field, filteredAdapters, condition) => {
    let excludedAdapters = ''
    if(fieldType === 'axonius' &&
        filteredAdapters &&
        field.indexOf('specific_data.data') !== -1 &&
        !filteredAdapters.selectAll &&
        !filteredAdapters.clearAll
    ){
        condition = condition.replace('specific_data.data.', 'data.')
        excludedAdapters = Object.keys(filteredAdapters.selectedValues).filter(key => !filteredAdapters.selectedValues[key]).join("', '");
    } else {
        return condition
    }
    return `specific_data == match([plugin_name not in [\'${excludedAdapters}\'] and ${condition}])`
}

export const getTypeFromField = (fieldName) => {
    /*
    Parse a field path to extract the prefix that indicates which Adapter it is from.
    If no such prefix, return the general field type
     */
    let fieldSpaceMatch = /adapters_data\.(\w+)\./.exec(fieldName)
    if (fieldSpaceMatch && fieldSpaceMatch.length > 1) {
        return fieldSpaceMatch[1]
    }
    return 'axonius'
}