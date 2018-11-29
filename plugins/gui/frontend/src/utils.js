export const validateNumber = (event) => {
    event = (event) ? event : window.event;
    let charCode = (event.which) ? event.which : event.keyCode;
    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
        event.preventDefault()
    } else {
        return true
    }
}