<template>
    <div class="cross">
        <div class="top"></div>
        <div class="bottom"></div>
    </div>
</template>

<script>
	export default {
		name: 'x-cross'
	}
</script>

<style lang="scss">
    .cross {
        display: flex;
        flex-direction: column;
        .top, .bottom {
            width: 6px;
            height: 6px;
            border-top: 1px solid;
            border-left: 1px solid;
        }
        .top {
            -webkit-transform: rotate(225deg);
            -moz-transform: rotate(225deg);
            -ms-transform: rotate(225deg);
            -o-transform: rotate(225deg);
            transform: rotate(225deg);
        }
        .bottom {
            margin-top: 2px;
            -webkit-transform: rotate(45deg);
            -moz-transform: rotate(45deg);
            -ms-transform: rotate(45deg);
            -o-transform: rotate(45deg);
            transform: rotate(45deg);
        }
    }
</style>