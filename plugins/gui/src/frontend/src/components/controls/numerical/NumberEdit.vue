<template>
    <input :id="schema.name" type="number" v-model="data" @focusout.stop="handleData" :class="{'invalid': !valid}"/>
</template>

<script>
	import PrimitiveMixin from '../primitive.js'

	export default {
		name: 'x-number-edit',
        mixins: [PrimitiveMixin],
        methods: {
			formatData() {
				return parseFloat(this.data)
            }
        }
	}
</script>

<style lang="scss">

</style>