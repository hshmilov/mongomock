<template>
    <ul class="x-nested-nav">
        <slot></slot>
    </ul>
</template>

<script>
    export default {
        name: 'x-nested-nav'
    }
</script>

<style lang="scss">
    .x-nested-nav {
        margin: 0px;
        padding: 0px;
        overflow: auto;
        flex: 1 0 auto;
        background: $theme-black;
        transition: all ease-in 0.2s;
    }
</style>