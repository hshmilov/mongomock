<template>
    <div class="x-range-edit">
        <div class="label">From</div>
        <input v-model="data.gte" type="text" @input="input" @focusout.stop="focusout" :class="{'error-border': error}" />
        <div class="label">To</div>
        <input v-model="data.lte" type="text" @input="input" @focusout.stop="focusout" :class="{'error-border': error}" />
    </div>
</template>

<script>
	import PrimitiveMixin from '../primitive.js'

	export default {
		name: 'x-range-edit',
		mixins: [PrimitiveMixin],
        created() {
			if (!this.data) {
				this.data = { lte: '', gte: '' }
            }
        }
	}
</script>

<style lang="scss">
    .x-range-edit {
        display: flex;
        .label {
            font-size: 12px;
            line-height: 30px;
            margin-right: 8px;
            font-style: italic;
        }
    }
</style>