<template>
    <div class="search-input" :class="{focus: focused}" @click="focus">
        <div class="input-icon">
            <svg-icon name="action/search" :original="true" height="18"></svg-icon>
        </div>
        <input type="text" v-model="searchValue" class="input-value" ref="input" :placeholder="placeholder"
               @input="updateSearchValue()" @focusout="focused = false" @click.stop="focused = true">
    </div>
</template>

<script>
    export default {
        name: 'x-search-input',
        props: [ 'value', 'placeholder' ],
        data() {
            return {
                searchValue: this.value,
                focused: false
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
            	this.focused = true
            	this.$refs.input.focus()
            }
        },
        mounted() {
        	this.focus()
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
            width: calc(100% - 64px);
            border: none;
            background: transparent;
            padding: 4px 4px 4px 42px;
        }
        .input-icon {
            border: 0;
            position: absolute;
            left: 0;
            top: 0;
            z-index: 100;
            padding: 0 12px;
            line-height: 30px;
            .svg-fill { fill: $grey-4 }
            .svg-stroke { stroke: $grey-4 }
        }
    }
</style>