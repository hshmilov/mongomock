<template>
    <div :class="`dynamic-popover dropdown-menu w-${size}`" :style="{left: left + 'px'}">
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'dynamic-popover',
        props: ['size', 'left']
	}
</script>

<style lang="scss">
    .dynamic-popover.dropdown-menu {
        display: block;
        top: -18px;
    }
</style>