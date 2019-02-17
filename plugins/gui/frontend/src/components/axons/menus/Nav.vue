<template>
    <ul class="x-nav">
        <slot></slot>
    </ul>
</template>

<script>
    export default {
        name: 'x-nav'
    }
</script>

<style lang="scss">
    .x-nav {
        margin: 0px;
        padding: 0px;
        flex: 1 0 auto;
        background: $theme-black;
        transition: all ease-in 0.2s;
    }
</style>