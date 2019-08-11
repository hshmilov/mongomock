export const validateNumber = (event) => {
    event = (event) ? event : window.event;
    let charCode = (event.which) ? event.which : event.keyCode;
    if (charCode === 46 || (charCode >= 48 && charCode <= 57) || charCode === 8) {
        return true
    }
    event.preventDefault()
}

export const validateInteger = (event) => {
    event = (event) ? event : window.event;
    let charCode = (event.which) ? event.which : event.keyCode;
    if ((charCode >= 48 && charCode <= 57) || charCode === 8) {
        return true
    }
    event.preventDefault()
}

export const formatDate = (dateString, schema) => {
    let dateTime = new Date(dateString);
    if (dateTime === 'Invalid Date') return value
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
