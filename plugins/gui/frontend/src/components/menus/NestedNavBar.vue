<template>
    <ul class="nav-nest">
        <slot></slot>
    </ul>
</template>

<script>
    export default {
        name: 'nested-nav-bar'
    }
</script>

<style lang="scss">
    .nav-nest {
        margin: 0px;
        padding: 0px;
    }

    .nav-item > .nav-nest {
        margin-left: 42px;
        li {
            text-transform: capitalize;
        }
    }
</style>