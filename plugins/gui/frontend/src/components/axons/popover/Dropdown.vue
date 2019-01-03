<template>
    <div class="x-dropdown" v-bind:class="{ active: isActive, disabled: readOnly }">
        <div :class="{trigger: true, arrow}" data-toggle="dropdown" aria-haspopup="true" :aria-expanded="isActive"
             @click="toggle" @keyup.enter="toggle" @keyup.down="open" @keyup.up="close" @keyup.esc="close">
            <slot name="trigger"></slot>
        </div>
        <div :class="`content ${sizeClass}`" :style="menuStyle" v-if="isActive" ref="content">
            <slot name="content"></slot>
        </div>
        <div @click="close" v-if="isActive" class="x-dropdown-bg"></div>
    </div>
</template>

<script>
    export default {
        name: 'x-dropdown',
        props: {
            size: {default: ''},
            align: {default: 'left'},
            alignSpace: {default: 0},
            alignAgile: {default: true},
            arrow: {default: true},
            readOnly: {default: false},
            container: {}
        },
        computed: {
            menuStyle() {
                if (!this.isActive) return {}
                let styles = {[this.align]: this.alignSpace + 'px'}
                if (this.align === 'right') {
                    styles['left'] = 'auto'
                } else {
                    styles['right'] = 'auto'
                }
                if (this.activated || !this.$refs.content || !this.alignAgile) return styles

                let bottomDistance = this.calcOffsetTop(this.$el) + this.$refs.content.offsetHeight
                if ((this.container && this.container.offsetHeight + this.container.offsetTop < bottomDistance)
                    || window.innerHeight < bottomDistance + 48) {
                    styles['bottom'] = '100%'
                    styles['top'] = 'auto'
                }
                return styles
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
            },
            calcOffsetTop(element) {
                if (element == null) {
                    return 0
                }
                return element.offsetTop + this.calcOffsetTop(element.offsetParent)
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
                min-width: 100%;
            }
        }

        .x-dropdown-bg {
            position: fixed;
            z-index: 299;
            background: transparent;
            height: 100vh;
            width: 100vw;
            top: 0;
            left: 0;
            cursor: default;
        }
    }
</style>