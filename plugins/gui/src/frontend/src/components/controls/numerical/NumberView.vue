<template>
    <div>{{ data.toFixed(2) }}</div>
</template>

<script>
	export default {
		name: 'x-number-view',
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