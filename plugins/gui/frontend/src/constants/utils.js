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
