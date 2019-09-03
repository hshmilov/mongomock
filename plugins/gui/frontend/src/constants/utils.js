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