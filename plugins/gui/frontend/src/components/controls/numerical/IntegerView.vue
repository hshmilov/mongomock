<template>
    <div>{{ processedData }}</div>
</template>

<script>
	export default {
		name: 'x-integer-view',
		props: ['schema', 'value'],
		computed: {
			processedData() {
				if (Array.isArray(this.value)) {
					return this.value.map(item => this.format(item)).join(', ')
				}
				return this.format(this.value)
			}
		},
		methods: {
			format(value) {
				if (typeof value === 'number') {
					return parseInt(value)
				}
				return ''
			}
		}
	}
</script>

<style lang="scss">

</style>