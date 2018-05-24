<template>
    <div class="x-box">
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'x-box'
	}
</script>

<style lang="scss">
    .x-box {
        padding: 24px;
        background-color: $theme-white;
        overflow: auto;
    }
</style>