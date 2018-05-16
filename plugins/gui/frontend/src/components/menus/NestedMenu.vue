<template>
    <div class="x-nested-menu">
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'x-nested-menu'
	}
</script>

<style lang="scss">
    .x-nested-menu {
        margin: 0 -12px;
    }
</style>