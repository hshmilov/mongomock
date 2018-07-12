<template>
    <div v-if="typeof processedData !== 'boolean'"></div>
    <div v-else-if="processedData">
        <div class="checkmark"></div>
    </div>
    <x-cross v-else />
</template>

<script>
    import xCross from '../../patterns/Cross.vue'

	export default {
		name: 'x-bool-view',
        components: { xCross },
        props: ['schema', 'value'],
        computed: {
			processedData() {
				if (Array.isArray(this.value)) {
					if (!this.value.length) return ''
					return this.value.reduce((current, accumulator) => {
						return current && accumulator
                    }, true)
                }
                return this.value
            }
        }
	}
</script>

<style lang="scss">
    .checkmark {
        width: 6px;
        height: 12px;
        -webkit-transform: rotate(45deg);
        -moz-transform: rotate(45deg);
        -ms-transform: rotate(45deg);
        -o-transform: rotate(45deg);
        transform: rotate(45deg);
        border-bottom: 1px solid;
        border-right: 1px solid;
        margin-left: 4px;
    }
</style>