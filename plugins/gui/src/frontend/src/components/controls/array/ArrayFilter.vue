<template>
    <input type="number" v-model="data" @input="input">
</template>

<script>
    import PrimitiveMixin from '../primitive'

	export default {
		name: 'x-array-filter',
        mixins: [PrimitiveMixin]
	}
</script>

<style lang="scss">

</style>