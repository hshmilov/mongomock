<template>
    <div class="menu-item" :class="{nested: nested, active: isActive}" @mouseover="isActive = true" tabindex="-1"
         @mouseout="isActive = false" @click="$emit('click')" @keyup.enter="$emit('click')"
         @keyup.up="$emit('keyup.up')" @keyup.down="$emit('keyup.down')">
        <div class="item-content">{{ title }}</div>
        <div v-show="isActive">
            <slot></slot>
        </div>
    </div>
</template>

<script>
	export default {
		name: 'nested-menu-item',
        props: {title: {required: true}, selected: {default: false}},
        computed: {
			nested() {
                return this.$slots !== undefined && this.$slots.default !== undefined && this.$slots.default.length
            }
        },
        data() {
			return {
				isActive: this.selected
            }
        },
        watch: {
			selected(newSelected) {
				this.isActive = newSelected
			},
            isActive(newIsActive) {
                if (newIsActive) {
					this.$el.focus()
                }
            }
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
        &.active {
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