<template>
    <x-checkbox v-model="data" @focusout.stop="focusout" @change="input" :class="{'error-border': error}"
                :read-only="readOnly" />
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
				this.$emit('input', this.data)
            }
        }
	}
</script>

<style lang="scss">
</style>