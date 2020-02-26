<template>
    <div class="x-dropdown" v-bind:class="{ active: isActive, disabled: readOnly }">
        <div class="dropdown-input">
            <div :class="{trigger: true, arrow}" data-toggle="dropdown" aria-haspopup="true" :aria-expanded="isActive"
                @click="toggle" @keyup.enter="toggle" @keyup.down="open" @keyup.up="close" @keyup.esc="close">
                <slot name="trigger"></slot>
            </div>
            <div @click="close" v-if="isActive" class="x-dropdown-bg"></div>
        </div>
        <div :class="`content ${sizeClass}`" :style="contentStyle" v-if="isActive" ref="content">
            <slot name="content"></slot>
        </div>
    </div>
</template>

<script>
    export default {
        name: 'x-dropdown',
        props: {
            size: {default: ''},
            align: {default: 'left'},
            alignAgile: {default: true},
            arrow: {default: true},
            readOnly: {default: false},
            overflow: {default: true},
        },
        computed: {
            sizeClass() {
                if (this.size) {
                    return `w-${this.size}`;
                }
                return '';
            }
        },
        data() {
            return {
                isActive: false,
                contentStyle: { bottom: 0, right: 0 },
            }
        },
        methods: {
            toggle() {
                if (!this.readOnly) {
                    this.isActive = !this.isActive;
                    this.activeChanged();
                }
            },
            open() {
                if (!this.readOnly) {
                    this.isActive = true;
                    this.activeChanged();
                }
            },
            close() {
                this.isActive = false;
            },
            activeChanged() {
                if(this.isActive){
                    this.$nextTick(() => {
                        this.calculateContentStyle();
                        this.$emit('activated');
                    });
                }
            },
            calculateContentStyle() {
                const styles = {};
                const boundingRect = this.$el.getBoundingClientRect();
                if (this.align === 'right') {
                    const right = window.innerWidth - boundingRect.x - boundingRect.width;
                    styles.right = `${right}px`;
                    styles.left = 'auto';
                }

                styles[this.overflow ? 'min-width' : 'max-width'] = `${boundingRect.width}px`;
                const dropdownInputBottom = boundingRect.top + this.$el.offsetHeight;

                if (!this.alignAgile){
                    styles['max-height'] = `calc(100% - ${dropdownInputBottom}px)`;
                    styles.overflow = 'auto';
                    this.contentStyle = styles;
                }
                
                const contentBottomPosition = dropdownInputBottom + this.$refs.content.offsetHeight;
                let top;
                if (contentBottomPosition > window.innerHeight) {
                    top = boundingRect.top - this.$refs.content.offsetHeight;
                } else {
                    top = dropdownInputBottom;
                }

                styles.top = `${top}px`;
                this.contentStyle = styles;
            },
        },
    }
</script>

<style lang="scss">
    .x-dropdown {

        .dropdown-input {
            position: relative;
        }

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
            position: fixed;
            z-index: 300;
            padding: 12px;
            border-radius: 4px;
            box-shadow: $popup-shadow;
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
