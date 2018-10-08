<template>
    <div class="x-dropdown" v-bind:class="{ active: isActive, disabled: readOnly }" v-on-clickaway="close">
        <div :class="{trigger: true, arrow: arrow}" data-toggle="dropdown" aria-haspopup="true" :aria-expanded="isActive"
             @click="toggle" @keyup.enter="toggle" @keyup.down="open" @keyup.up="close" @keyup.esc="close">
            <slot name="trigger"></slot>
        </div>
        <div :class="`content ${sizeClass}`" :style="{[align]: alignSpace + 'px', [alignAuto]: 'auto'}" v-if="isActive">
            <slot name="content"></slot>
        </div>
    </div>
</template>

<script>
    import { mixin as clickaway } from 'vue-clickaway'

    export default {
        name: 'x-dropdown',
        mixins: [ clickaway ],
        props: {
            size: {default: ''},
            align: {default: 'left'},
            alignSpace: {default: 0},
            arrow: {default: true},
            readOnly: { default: false }
        },
        computed: {
        	alignAuto() {
        		if (this.align === 'right') return 'left'
                return 'right'
            },
            sizeClass() {
        		if (this.size) {
        			return `w-${this.size}`
                }
                return 'expand'
            }
        },
        data() {
            return {
                isActive: false,
                activated: false
            }
        },
        watch: {
        	isActive(newIsActive) {
        		this.activated = newIsActive
            }
        },
        methods: {
        	open() {
        	    if (!this.readOnly) {
        	        this.isActive = true
                }
            },
            toggle() {
        	    if (!this.readOnly) {
                    this.isActive = !this.isActive
                    this.$emit('click')
                }
            },
        	close() {
        		this.isActive = false
            }
        },
        updated() {
            if (this.activated) {
            	this.$emit('activated')
                this.activated = false
            }
        }
    }
</script>

<style lang="scss">
    .x-dropdown {
        position: relative;
        .trigger {
            cursor: pointer;
            &.arrow:after {
                right: 8px;
                @include triangle('down', 0.35rem);
            }
        }
        &.disabled .trigger {
            cursor: default;
        }
        > .content {
            background-color: $theme-white;
            position: absolute;
            z-index: 300;
            top: 96%;
            padding: 12px;
            border-radius: 4px;
            box-shadow: $popup-shadow;
            &.expand {
                width: calc(100% - 24px);
            }
        }
    }
</style>