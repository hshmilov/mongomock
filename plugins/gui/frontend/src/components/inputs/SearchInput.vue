<template>
    <div class="search-input" @keyup.esc="$emit('keyup.esc')">
        <input type="text" v-model="searchValue" class="input-value" @input="updateSearchValue()" :placeholder="placeholder"
               ref="input" @keydown.prevent.down="$emit('keydown.down')" @keydown.prevent.up="$emit('keydown.up')">
        <span class="input-addon">
            <svg-icon name="action/search" :original="true" height="18"></svg-icon>
        </span>
    </div>
</template>

<script>
    export default {
        name: 'x-search-input',
        props: [ 'value', 'placeholder' ],
        data() {
            return {
                searchValue: this.value
            }
        },
        methods: {
            updateSearchValue() {
                this.$emit('input', this.searchValue)
            },
            focus() {
            	this.$refs.input.focus()
            }
        }
    }
</script>

<style lang="scss">
    .search-input {
        padding: 0 12px;
        .input-value {
            width: 100%;
            border: 0;
            border-bottom: 1px solid $grey-2;
            height: 30px;
            padding: 4px;
            &:focus {
                border-color: $theme-blue;
                outline: none;
            }
        }
        .input-addon {
            border: 0;
            position: absolute;
            right: 0;
            top: 0;
            z-index: 100;
            height: 30px;
            padding: 0 12px;
            background-color: transparent;
            font-size: 150%;
            .svg-fill { fill: $theme-black }
            .svg-stroke { stroke: $theme-black }
        }
    }
</style>