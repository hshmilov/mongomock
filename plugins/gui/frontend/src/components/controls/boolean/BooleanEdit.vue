<template>
    <x-checkbox v-model="data" @focusout.stop="validate" @change="input" :class="{'invalid': !valid}" />
</template>

<script>
    import xCheckbox from '../../inputs/Checkbox.vue'
    import PrimitiveMixin from '../primitive.js'

	export default {
		name: 'x-bool-edit',
        mixins: [PrimitiveMixin],
        components: { xCheckbox },
        methods: {
			isEmpty() {
				return this.data === undefined || typeof this.data !== 'boolean'
            }
        },
        created() {
			if (!this.data) {
				this.data = false
                this.input()
                this.validate()
            }
        }
	}
</script>

<style lang="scss">
</style>