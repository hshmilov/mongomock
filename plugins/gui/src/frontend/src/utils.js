const pad2 = (number) => {
	/*
		Add leading zero for 1 digit numbers - to keep a constant format of date and time
	 */
	if ((number + '').length >= 2) { return number }
	return `0${number}`
}

export const parseDate = (timestamp) => {
	/*
		Convert given timestamp to a date by the format dd/mm/yyyy
	 */
	let d = new Date(timestamp)
	return [pad2(d.getDate()), pad2(d.getMonth()+1), pad2(d.getFullYear())].join('/')
}

export const parseTime = (timestamp) => {
	/*
		Convert given timestamp to a time by the format hh:mm
	 */
	let d = new Date(timestamp)
	return [pad2(d.getHours()), pad2(d.getMinutes())].join(':')
}