const getEventKey = (e) => {
    return (e || window.event).key
}

export const validateNumber = (e) => {
    const key = getEventKey(e)
    if (key.match(new RegExp('[0-9.]'))) {
        return true
    }
    event.preventDefault()
}

export const validateInteger = (e, allowNegative) => {
    const key = getEventKey(e)
    const regex = allowNegative ? '[-0-9]' : '[0-9]';
    if (key.match(new RegExp(regex))) {
        return true
    }
    event.preventDefault()
}

export const validateFieldName = (e) => {
    const key = getEventKey(e)
    if (key.match(new RegExp('[a-zA-Z_0-9 ]'))) {
        return true
    }
    event.preventDefault()
}

export const validateEmail = (value) => {
    return value.match(new RegExp('^"?[\\w.+\\- ]{1,64}"?@[a-zA-Z_\\-0-9]+?(\\.[a-zA-Z]+){0,2}$'))
}


