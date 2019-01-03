<template>
    <input v-else type="number" v-model="data" @input="input">
</template>

<script>
    import PrimitiveMixin from '../primitive'
    import xStringEdit from '../string/StringEdit.vue'

	export default {
		name: 'x-array-filter',
        mixins: [PrimitiveMixin]
	}
</script>

<style lang="scss">

</style>