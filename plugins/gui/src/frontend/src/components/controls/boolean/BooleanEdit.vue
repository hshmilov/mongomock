<template>
    <checkbox v-model="data" @focusout.stop="handleData" :class="{'invalid': !valid}"></checkbox>
</template>

<script>
    import Checkbox from '../../Checkbox.vue'
    import PrimitiveMixin from '../primitive.js'

	export default {
		name: 'x-bool-edit',
        mixins: [PrimitiveMixin],
        components: { Checkbox },
        methods: {
			isEmpty() {
				return this.data === undefined || typeof this.data !== 'boolean'
            }
        },
        created() {
			if (!this.data) {
				this.data = false
                this.handleData()
            }
        }
	}
</script>

<style lang="scss">
</style>