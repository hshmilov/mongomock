<template>
    <div class="input-group search-input">
        <input type="text" v-model="searchValue" class="search-value form-control" @input="updateSearchValue()"
               :placeholder="placeholder">
        <span class="input-group-addon">
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
            }
        }
    }
</script>

<style lang="scss">
    .search-input.input-group {
        display: inline-block;
        .search-value.form-control {
            width: 100%;
            border-radius: 2px;
            border: 1px solid $grey-2;
            height: 30px;
            &:focus {
                border-color: $theme-blue;
            }
        }
        .input-group-addon {
            border: 0;
            position: absolute;
            right: 0;
            top: 0;
            z-index: 100;
            height: 30px;
            padding-right: 8px;
            padding-left: 8px;
            background-color: transparent;
            font-size: 150%;
            .svg-fill { fill: $theme-black }
            .svg-stroke { stroke: $theme-black }
        }
    }
</style>