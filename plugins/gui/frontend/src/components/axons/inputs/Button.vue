<template>
    <button class="x-button" :class="{disabled, inverse, light, right, link, great, emphasize, active}"
            @click="onClick"><slot /></button>
</template>

<script>
    export default {
        name: 'x-button',
        props: {
            disabled: {
                type: Boolean,
                default: false
            },
            inverse: {
                type: Boolean,
                default: false
            },
            light: {
                type: Boolean,
                default: false
            },
            right: {
                type: Boolean,
                default: false
            },
            link: {
                type: Boolean,
                default: false
            },
            great: {
                type: Boolean,
                default: false
            },
            emphasize: {
                type: Boolean,
                default: false
            },
            active: {
                type: Boolean,
                default: false
            }
        },
        methods: {
            onClick(e) {
                if (this.disabled) {
                    this.$emit('access')
                    e.preventDefault()
                    return false
                }
                this.$emit('click', e)
                return true
            }
        }
    }
</script>

<style lang="scss">
    .x-button {
        border: 0;
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.2s ease-in;
        color: $theme-white;
        background-color: $theme-blue;
        padding: 4px 12px;
        text-align: center;
        width: 120px;
        font: 300 14px Roboto;
        line-height: 20px;
        &:hover {
            color: $theme-white;
            &:not(.disabled) {
                box-shadow: 0px 4px 8px 0px rgba(0, 0, 0, 0.2);
            }
        }
        &.disabled {
            opacity: 0.4;
            cursor: default;
            &:hover {
                box-shadow: none;
            }
            &:focus {
                outline: none;
            }
        }
        &.inverse {
            background-color: $theme-white;
            color: $theme-blue;
            border: 1px solid $theme-blue;
        }
        &.light {
            background-color: $grey-2;
            color: $theme-black;
            width: 30px;
            height: 30px;
            line-height: 24px;
            padding: 4px 0;
            &.active {
                background-color: $theme-black;
                color: $grey-2;
            }
        }
        &.right {
            width: auto;
            padding: 3px 12px;
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
        }
        &.link {
            width: auto;
            background-color: transparent;
            color: $theme-blue;
            border: 0;
            .svg-fill { fill: $theme-blue; }
            .svg-stroke { stroke: $theme-blue; }
            &:hover {
                box-shadow: none;
                &:not(.disabled) {
                    text-shadow: $text-shadow;
                    .svg-fill { fill: $theme-orange; }
                    .svg-stroke { stroke: $theme-orange; }
                }
            }
        }
        &.great {
            font-size: 16px;
            line-height: 30px;
        }
        &.emphasize {
            background-color: $theme-orange;
        }
        .svg-fill { fill: $theme-white; }
        .svg-stroke { stroke: $theme-white; }
    }
</style>