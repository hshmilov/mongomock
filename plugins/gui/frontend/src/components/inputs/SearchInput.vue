<template>
    <div class="search-input" @keyup.esc="$emit('keyup.esc')" :class="{focus: isFocus}" @click="focus">
        <input type="text" v-model="searchValue" class="input-value" ref="input" :placeholder="placeholder"
               @input="updateSearchValue()" @focusout="isFocus = false"
               @keydown.prevent.down="$emit('keydown.down')" @keydown.prevent.up="$emit('keydown.up')">
        <div class="input-icon">
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
                searchValue: this.value,
                isFocus: false
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
            	this.isFocus = true
            	this.$refs.input.focus()
            }
        }
    }
</script>

<style lang="scss">
    .search-input {
        padding: 0 12px;
        position: relative;
        border: 1px solid $grey-2;
        background: $grey-dient;
        &.focus {
            border-color: $theme-blue;
        }
        .input-value {
            width: calc(100% - 36px);
            border: none;
            background: transparent;
            padding: 4px;
        }
        .input-icon {
            border: 0;
            position: absolute;
            right: 0;
            top: 0;
            z-index: 100;
            padding: 0 12px;
            line-height: 30px;
            .svg-fill { fill: $theme-black }
            .svg-stroke { stroke: $theme-black }
        }
    }
</style>