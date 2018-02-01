<template>
    <div class="menu">
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'nested-menu'
	}
</script>

<style lang="scss">
    .menu {
        margin: 0 -12px;
    }
</style>