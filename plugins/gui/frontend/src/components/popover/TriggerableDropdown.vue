<template>
    <div class="dropdown" v-bind:class="{ 'show': isActive }" v-on-clickaway="close" v-on:mouseout="$emit('mouseout')">
        <div class="dropdown-toggle" :class="{'arrow': arrow}" @click="isActive = !isActive"
             data-toggle="dropdown" aria-haspopup="true" :aria-expanded="`${isActive}`">
            <slot name="trigger"></slot>
        </div>
        <div :class="`dropdown-menu w-${size}`" :style="{[align]: alignSpace + 'px', [alignAuto]: 'auto'}">
            <slot name="content"></slot>
        </div>
    </div>
</template>

<script>
    import { mixin as clickaway } from 'vue-clickaway'

    export default {
        name: 'triggerable-dropdown',
        mixins: [ clickaway ],
        props: {size: {default: ''}, align: {default: 'left'}, alignSpace: {default: 0}, arrow: {default: true}},
        computed: {
        	alignAuto() {
        		if (this.align === 'right') return 'left'
                return 'right'
            }
        },
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
    .dropdown {
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
                right: 12px;
                @include triangle('down', 0.35rem);
                transition: transform ease-in-out 0.5s;
            }
        }
    }
    .dropdown.show {
        > .dropdown-menu {
            display: block;
            border-color: $grey-2;
        }
        > .dropdown-toggle:after {
            transform: rotate(180deg);
        }
    }
</style>