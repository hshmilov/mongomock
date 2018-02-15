<template>
    <div>{{ data? parseInt(data) : '' }}</div>
</template>

<script>
	export default {
		name: 'x-integer-view',
		props: ['schema', 'value'],
		data() {
			return {
				data: this.value
			}
		}
	}
</script>

<style lang="scss">

</style>