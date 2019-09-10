<template>
    <x-checkbox v-model="data" @focusout.stop="focusout" @change="input" :class="{'error-border': error}"
                :read-only="readOnly" :id="schema.name" />
</template>

<script>
    import xCheckbox from '../../../../axons/inputs/Checkbox.vue'
    import primitiveMixin from '../primitive.js'

	export default {
		name: 'x-bool-edit',
        mixins: [primitiveMixin],
        components: { xCheckbox },
        methods: {
			isEmpty() {
				return this.data === undefined || typeof this.data !== 'boolean'
            }
        }
	}
</script>

<style lang="scss">
</style>