<template>
    <div :class="`${customClass? customClass: ''} card`">
        <div v-if="title" class="card-header">
            <span class="card-header-title">{{ title }}</span>
            <slot v-if="$slots['cardActions']" name="cardActions"></slot>
        </div>
        <div class="card-body">
            <slot name="cardContent"></slot>
        </div>
    </div>
</template>

<script>
    export default {
        name: 'card',
        props: ['customClass', 'title']
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .card {
        margin-bottom: 12px;
        .card-header {
            padding: 8px 12px;
            display: flex;
            flex-direction: row;
            -ms-flex-direction: row;
            flex-basis: 100%;
            -ms-flex-preferred-size: 100%;
            background-color: $background-color-light;
            .card-header-title {
                flex: 1 1 auto;
                text-transform: capitalize;
                letter-spacing: 0.5px;
                line-height: 30px;
            }
            .card-actions {
                flex: 0 1 auto;
                display: flex;
                flex-flow: row;
                .dropdown {
                    margin-left: 12px;
                    &:hover, &.show {
                        background-color: rgba(235, 233, 250, 0.6);
                        border-color: $color-theme-light;
                    }
                }
            }
        }
        .card-body {
            position: relative;
            padding: 12px 12px;
        }
    }
</style>