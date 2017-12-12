<template>
    <ul class="action-bar">
        <li v-for="action in actions" class="action-bar-item">
            <a @click="action.handler">{{ action.title }}</a>
        </li>
    </ul>
</template>

<script>
    export default {
        name: 'action-bar',
        props: [ 'actions' ]
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .action-bar {
        margin-bottom: 0;
        line-height: 30px;
        .action-bar-item {
            display: inline-block;
            font-size: 80%;
            letter-spacing: 0.5px;
            list-style: none;
            color: $color-theme-light;
            padding-left: 12px;
            padding-right: 12px;
            border-left: 1px solid $color-text-title;
            transition: text-shadow 0.3s ease;
            &:first-of-type {
                border-left: 0;
            }
            &:hover {
                color: $color-warning;
            }
        }
    }
</style>