<template>
    <div class="dynamic-popover dropdown-menu" :class="`w-${size} ${alignBottomClass}`"
         :style="{left: left + 'px'}">
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'dynamic-popover',
        props: ['size', 'left', 'alignBottom'],
        computed: {
			alignBottomClass() {
				if (this.alignBottom) return 'bottom'
				return ''
            }
        }
	}
</script>

<style lang="scss">
    .dynamic-popover.dropdown-menu {
        display: block;
        top: -40px;
        &.bottom {
            top: auto;
            bottom: -18px;
        }
    }
</style>