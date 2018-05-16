<template>
    <div class="search-input" @keyup.esc="$emit('keyup.esc')">
        <input type="text" v-model="searchValue" class="input-value" @input="updateSearchValue()" :placeholder="placeholder"
               ref="input" @keydown.prevent.down="$emit('keydown.down')" @keydown.prevent.up="$emit('keydown.up')">
        <div class="input-addon">
            <svg-icon name="action/search" :original="true" height="18"></svg-icon>
        </div>
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
        watch: {
        	value(newValue) {
        		this.searchValue = newValue
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
        position: relative;
        .input-value {
            width: 100%;
            border: 1px solid $grey-2;
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
            padding: 0 12px;
            background-color: transparent;
            line-height: 30px;
            .svg-fill { fill: $theme-black }
            .svg-stroke { stroke: $theme-black }
        }
    }
</style>