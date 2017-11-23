<template>
    <div class="checkbox" v-bind:class="{ 'checked': checked }" @click.stop="$refs.checkboxInput.click()">
        <input type="checkbox" ref="checkboxInput" :checked="checked" @change="updateChecked()"
               :disabled="disabled">
        <label class="checkbox-label">{{ label }}</label>
    </div>
</template>

<script>
    export default {
        name: 'checkbox',
        model: {
            prop: 'checked',
            event: 'change'
        },
        props: [ 'label', 'checked', 'disabled' ],
        methods: {
            updateChecked() {
                this.$emit('change', this.$refs.checkboxInput.checked)
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .checkbox {
        position: relative;
        line-height: 24px;
        input[type=checkbox] {
            visibility: hidden;
            &+label:before {
                content: '';
                position: absolute;
                cursor: pointer;
                top: 0;
                left: 0;
                width: 18px;
                height: 18px;
                z-index: 0;
                border: 1px solid #b1b8bb;
                border-radius: 1px;
                margin-top: 2px;
                -webkit-transition: .2s;
                -o-transition: .2s;
                transition: .2s;
            }
            &:checked+label:before {
                top: -4px;
                left: -2px;
                width: 10px;
                height: 18px;
                border-top: 2px solid transparent;
                border-left: 2px solid transparent;
                border-right: 2px solid $color-theme;
                border-bottom: 2px solid $color-theme;
                -webkit-transform: rotate(40deg);
                -ms-transform: rotate(40deg);
                transform: rotate(40deg);
                -webkit-backface-visibility: hidden;
                backface-visibility: hidden;
                -webkit-transform-origin: 100% 100%;
                -ms-transform-origin: 100% 100%;
                transform-origin: 100% 100%;
            }
        }
        .checkbox-label {
            margin-left: 8px;
            margin-bottom: 0;
            &:empty {
                margin-left: 0;
            }
        }
        .checkbox-skin {
            border-radius: 4px;
            height: 20px;
            width: 20px;
            border: 1px solid $border-color;
            background: transparent;
            position: absolute;
            top: 2px;
        }
        &:hover .checkbox-skin {
            border-color: $color-theme;
        }
        .checkbox-check {
            display: inline;
            position: absolute;
            left: 2px;
            top: 8px;
            width: 0;
            height: 0;
            -webkit-transition: width 0.3s ease, height 0.3s ease;
            -moz-transition: width 0.3s ease, height 0.3s ease;
            -o-transition: width 0.3s ease, height 0.3s ease;
            transition: width 0.3s ease, height 0.3s ease;
        }
        &.checked .checkbox-check {
            -webkit-transform: rotate(-45deg);
            -moz-transform: rotate(-45deg);
            -o-transform: rotate(-45deg);
            transform: rotate(-45deg);
            width: 16px;
            height: 6px;
            border-left: 2px solid $color-theme;
            border-bottom: 2px solid $color-theme;
            border-right: 2px solid transparent;
            border-top: 2px solid transparent;
        }
    }
</style>