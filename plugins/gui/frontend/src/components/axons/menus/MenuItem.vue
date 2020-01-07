<template>
    <div class="x-menu-item" :class="{nested: nested, active: isActive, disabled: disabled }" @mouseover="isActive = true" tabindex="-1"
         @mouseout="isActive = false" @click="onClick" @keyup.enter="onClick">
        <div class="item-content">{{ title }}
            <svg-icon
                v-if="disabled"
                name="symbol/info"
                :original="true" height="16"
                :title="disabledDescription"
            />
        </div>
        <div v-show="isActive && !disabled">
            <slot></slot>
        </div>
    </div>
</template>

<script>
    export default {
        name: 'x-menu-item',
        props: {
            title: {required: true},
            selected: {default: false},
            disabled: {
                type: Boolean,
                default: false
            },
            disabledDescription: {
                type: String,
                default: ''
            }
            },
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
        watch: {
            selected(newSelected) {
                this.isActive = newSelected
            },
            isActive(newIsActive) {
                if (newIsActive) {
                    this.$el.focus()
                }
            }
        },
        created() {
            this.isActive = this.selected
        },
        methods: {
            onClick() {
                if (!this.disabled) {
                    this.$emit('click')
                }
            }
        }
    }
</script>

<style lang="scss">
    .x-menu-item {
        color: $theme-black;
        cursor: pointer;
        padding-right: 12px;
        padding-left: 12px;
        margin: 4px 0px;
        position: relative;

        &.disabled {
            opacity: 0.6;
            cursor: default;
        }

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

        svg {
            float: right;
            margin-top: 4px;
        }
    }
</style>
