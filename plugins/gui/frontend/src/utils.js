export const validateNumber = (event) => {
    event = (event) ? event : window.event;
    let charCode = (event.which) ? event.which : event.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
        event.preventDefault()
        return false
    }
    return true
}

export const validateInteger = (event) => {
    event = (event) ? event : window.event;
    let charCode = (event.which) ? event.which : event.keyCode;
    if ((charCode > 31 && (charCode < 48 || charCode > 57)) || charCode === 190 ) {
        event.preventDefault()
        return false
    }
    return true
}