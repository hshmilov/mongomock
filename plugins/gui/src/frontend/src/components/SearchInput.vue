<template>
    <div class="input-group search-input">
        <input type="text" v-model="searchValue" class="search-value form-control" @input="updateSearchValue()">
        <span class="input-group-addon"><i class="icon-search"></i></span>
    </div>
</template>

<script>
    export default {
        name: 'search-input',
        props: [ 'value' ],
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
    @import '../scss/config';

    .search-input.input-group {
        display: inline-block;
        .search-value.form-control {
            width: 100%;
            border-radius: 4px;
            border: 1px solid $border-color;
            height: 30px;
            &:focus {
                border-color: $color-theme;
            }
        }
        margin-bottom: 12px;
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
            color: $border-color;
            font-size: 150%;
            &:hover {
                color: $color-theme;
                cursor: pointer;
            }
        }
    }
</style>