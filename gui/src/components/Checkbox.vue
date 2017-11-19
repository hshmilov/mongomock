<template>
    <div class="checkbox" v-bind:class="{ 'checked': checked }" @click="$refs.checkboxInput.click()">
        <input type="checkbox" ref="checkboxInput" :checked="checked" @change="updateChecked()">
        <div class="checkbox-skin"></div><div class="checkbox-check"></div>
        <label v-if="label" class="checkbox-label">{{ label }}</label>
    </div>
</template>

<script>
    export default {
        name: 'checkbox',
        model: {
            prop: 'checked',
            event: 'change'
        },
        props: [ 'label', 'checked' ],
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
        width: 24px;
        line-height: 24px;
        input[type=checkbox] {
            visibility: hidden;
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
        .checkbox-label {
            margin-left: 8px;
            margin-bottom: 0;
        }
    }
</style>