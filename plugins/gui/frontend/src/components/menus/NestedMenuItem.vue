<template>
    <div class="menu-item" :class="{'nested': nested}" @mouseover="isActive = true; $emit('mouseover')"
         @mouseout="isActive = false" @click="$emit('click')">
        <div>{{ title }}</div>
        <div v-show="isActive">
            <slot></slot>
        </div>
    </div>
</template>

<script>
	export default {
		name: 'nested-menu-item',
        props: {'title': {required: true}, 'selected': {default: false}},
        computed: {
			nested() {
                return this.$slots !== undefined && this.$slots.default !== undefined && this.$slots.default.length
            }
        },
        data() {
			return {
				isActive: false
            }
        },
        created() {
			this.isActive = this.selected
        }
	}
</script>

<style lang="scss">
    .menu-item {
        color: $theme-black;
        cursor: pointer;
        padding-right: 12px;
        padding-left: 12px;
        margin: 4px 0px;
        position: relative;
        &:hover {
            background-color: $grey-2;
        }
        &.nested {
            position: relative;
            &::after {
                content: '';
                position: absolute;
                top: 8px;
                right: 8px;
                display: inline-block;
                border-right: 1px solid $theme-black;
                border-top: 1px solid $theme-black;
                width: 8px;
                height: 8px;
                transform: rotate(45deg);
            }
        }
    }
</style>