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
        -webkit-box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.1);
        box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 12px;
        &.aqua {
            border-color: $color-aqua;
            .card-header {
                background-color: $color-aqua;
                color: $color-light;
                border-bottom-color: $color-aqua;
            }
        }
        .card-header {
            padding: 8px 12px;
            display: flex;
            flex-direction: row;
            -ms-flex-direction: row;
            flex-basis: 100%;
            -ms-flex-preferred-size: 100%;
            .card-header-title {
                flex: 1 1 auto;
                text-transform: capitalize;
                letter-spacing: 0.5px;
                font-weight: 500;
                line-height: 30px;
            }
            .card-actions {
                flex: 0 1 auto;
                display: flex;
                flex-flow: row;
                .dropdown {
                    margin-left: 8px;
                    &:hover, &.show {
                        background-color: rgba(235, 233, 250, 0.6);
                        border-color: $color-theme;
                    }
                    .dropdown-menu {
                        width: 200px;
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