<template>
    <input type="number" v-model="data" @input="input">
</template>

<script>
    import primitiveMixin from '../primitive'

	export default {
		name: 'x-array-filter',
        mixins: [primitiveMixin]
	}
</script>

<style lang="scss">

</style>