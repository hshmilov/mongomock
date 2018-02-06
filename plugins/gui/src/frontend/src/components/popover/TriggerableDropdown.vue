<template>
    <div class="dropdown" v-bind:class="{ 'show': isActive }" v-on-clickaway="close">
        <div class="dropdown-toggle" :class="{'arrow': arrow}" @click="isActive = !isActive"
             data-toggle="dropdown" aria-haspopup="true" :aria-expanded="`${isActive}`">
            <slot name="dropdownTrigger"></slot>
        </div>
        <div :class="`dropdown-menu ${align} w-${size}`">
            <slot name="dropdownContent"></slot>
        </div>
    </div>
</template>

<script>
    import { mixin as clickaway } from 'vue-clickaway'

    export default {
        name: 'triggerable-dropdown',
        mixins: [ clickaway ],
        props: {'size': {default: ''}, 'align': {default: ''}, arrow: {default: true}},
        data() {
            return {
                isActive: false
            }
        },
        methods: {
        	close() {
        		this.isActive = false
            }
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
                display: none;
            }
            &.arrow:after {
                display: inline-block;
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