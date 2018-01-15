<template>
    <div>
        <div v-if="value">
            <div class="checkmark"></div>
        </div>
        <div class="d-flex flex-column" v-else>
            <div class="cross top"></div>
            <div class="cross bottom"></div>
        </div>
    </div>
</template>

<script>
	export default {
		name: 'boolean',
        props: ['data']
	}
</script>

<style lang="scss">
    .checkmark {
        width: 4px;
        height: 12px;
        -webkit-transform: rotate(45deg);
        -moz-transform: rotate(45deg);
        -ms-transform: rotate(45deg);
        -o-transform: rotate(45deg);
        transform: rotate(45deg);
    }
    .cross {
        width: 6px;
        height: 6px;
        border-top: 1px solid;
        border-left: 1px solid;
        &.top {
            -webkit-transform: rotate(135deg);
            -moz-transform: rotate(135deg);
            -ms-transform: rotate(135deg);
            -o-transform: rotate(135deg);
            transform: rotate(135deg);
        }
        &.bottom {
            -webkit-transform: rotate(45deg);
            -moz-transform: rotate(45deg);
            -ms-transform: rotate(45deg);
            -o-transform: rotate(45deg);
            transform: rotate(45deg);
        }
    }
</style>