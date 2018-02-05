<template>
    <date-picker :date="date" :option="dateTimeOption" @change="$emit('input', date.time)"></date-picker>
</template>

<script>
	import DatePicker from 'vue-datepicker'

	export default {
		name: 'x-date-edit',
		components: { 'date-picker': DatePicker },
        props: ['value'],
        computed: {
			dateTimeOption() {
				return {
					type: 'min',
					week: ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
					month: ['January', 'February', 'March', 'April', 'May', 'June',
						'July', 'August', 'September', 'October', 'November', 'December'],
					format: 'MM/DD/YYYY HH:mm',
					placeholder: '',
					inputStyle: {},
					color: {
						header: '#1d212c',
						headerText: '#f26739'
					}
				}
			}
        },
        data() {
			return {
				date: { time: this.value }
            }
        }
	}
</script>

<style lang="scss">

</style>