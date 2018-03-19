<template>
    <div v-if="typeof processedData !== 'boolean'"></div>
    <div v-else-if="processedData">
        <div class="checkmark"></div>
    </div>
    <div class="d-flex flex-column" v-else>
        <div class="cross top"></div>
        <div class="cross bottom"></div>
    </div>
</template>

<script>
	export default {
		name: 'x-bool-view',
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
    .cross {
        width: 6px;
        height: 6px;
        border-top: 1px solid;
        border-left: 1px solid;
        &.top {
            -webkit-transform: rotate(225deg);
            -moz-transform: rotate(225deg);
            -ms-transform: rotate(225deg);
            -o-transform: rotate(225deg);
            transform: rotate(225deg);
        }
        &.bottom {
            margin-top: 2px;
            -webkit-transform: rotate(45deg);
            -moz-transform: rotate(45deg);
            -ms-transform: rotate(45deg);
            -o-transform: rotate(45deg);
            transform: rotate(45deg);
        }
    }
</style>