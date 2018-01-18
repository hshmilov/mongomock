<template>
    <div class="dropdown" v-bind:class="{ 'show': isActive }" v-on-clickaway="closeDropdown">
        <div class="dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" :aria-expanded="`${isActive}`"
            @click="isActive = !isActive">
            <slot name="dropdownTrigger"></slot>
        </div>
        <div :class="`dropdown-menu right w-${size}`">
            <slot name="dropdownContent"></slot>
        </div>
    </div>
</template>

<script>
    import { mixin as clickaway } from 'vue-clickaway'

    export default {
        name: 'triggerable-dropdown',
        mixins: [ clickaway ],
        props: {'size': {default: 'md'}, 'active': {default: false}},
        data() {
            return {
                isActive: false
            }
        },
        methods: {
            closeDropdown() {
                this.isActive = false
            }
        },
        created() {
        	this.isActive = this.active
        }
    }
</script>

<style lang="scss">
    @import '../../scss/config';

    .dropdown {
        .dropdown-menu {
            &.right {
                right: 0;
                left: auto;
            }
            .checkbox {
                margin-top: 8px;
                width: 100%;
                &:first-of-type {
                    margin-top: 0;
                }
            }
        }
        .dropdown-toggle {
            cursor: pointer;
            font-size: 80%;
            padding-right: 4px;
            padding-left: 4px;
            i, .svg-icon {
                height: 24px;
                margin-top: 2px;
                font-size: 18px;
                vertical-align: middle;
                line-height: 28px;
            }
            &:after {
                position: absolute;
                margin: 6px 12px;
                top: 0;
                right: 0;
                width: 12px;
                height: 12px;
                border-top: 1px solid $color-text-main;
                border-left: 1px solid $color-text-main;
                border-right: 0;
                transform: rotate(225deg);
                transition: transform 0.2s;
            }
        }
    }
    .dropdown.show {
        > .dropdown-menu {
            display: block;
        }
        > .dropdown-toggle:after {
            transform: rotate(45deg);
            margin: 12px 12px;
        }
    }
</style>