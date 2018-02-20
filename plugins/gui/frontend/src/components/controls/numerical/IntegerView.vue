<template>
    <div>{{ value? parseInt(value) : '' }}</div>
</template>

<script>
	export default {
		name: 'x-integer-view',
		props: ['schema', 'value']
	}
</script>

<style lang="scss">

</style>