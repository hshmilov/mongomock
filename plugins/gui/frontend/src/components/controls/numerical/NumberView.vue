<template>
    <div>{{ typeof value === 'number'? value.toFixed(2) : '' }}</div>
</template>

<script>
	export default {
		name: 'x-number-view',
        props: ['schema', 'value']
	}
</script>

<style lang="scss">

</style>