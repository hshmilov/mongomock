<template>
    <ul class="nav-nest" :class="nestClass">
        <slot></slot>
    </ul>
</template>

<script>
    export default {
        name: 'nested-nav-bar',
        props: [ 'nestLevel' ],
        computed: {
            nestClass() {
                let level = (!this.nestLevel)? 0 : this.nestLevel
                return "nest-" + level
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .nav-nest {
        margin: 0px;
        padding: 0px;
    }

    .nav-nest.nest-1 {
        margin-left: 42px;
        li {
            text-transform: capitalize;
        }
    }
</style>