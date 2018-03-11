<template>
    <div class="dynamic-popover dropdown-menu" :class="`w-${size} ${alignBottomClass}`"
         :style="style">
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'dynamic-popover',
        props: ['size', 'left', 'top', 'alignBottom'],
        computed: {
			alignBottomClass() {
				if (this.alignBottom) return 'bottom'
				return ''
            },
            style() {
				let styleProps = {}
				if (this.left !== undefined) styleProps['left'] = this.left + 'px'
				if (this.top !== undefined) styleProps['top'] = this.top + 'px'
                return styleProps
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