<template>
    <input :id="schema.name" type="number" v-model="data" :class="{'invalid': !valid}"
           @focusout.stop="validate" @input="input"/>
</template>

<script>
	import PrimitiveMixin from '../primitive.js'

	export default {
		name: 'x-integer-edit',
        mixins: [PrimitiveMixin],
        methods: {
			formatData() {
				return parseInt(this.data)
            }
        }
	}
</script>

<style lang="scss">

</style>