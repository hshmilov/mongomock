<template>
    <div :class="`${customClass? customClass: ''} card`">
        <div class="card-header">
            <span v-if="title" class="card-header-title">{{ title }}</span>
            <slot name="cardActions"></slot>
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
        }
        .card-body {
            padding: 8px 12px;
        }
    }
</style>