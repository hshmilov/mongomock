<template>
    <router-link tag="li" :to="{ name: routeName }" active-class="active" class="nav-item">
        <a class="nav-link" v-bind:class="{ 'has-arrow': hasSlot }">
            <svg-icon v-if="iconName" :name="`navigation/${iconName}`" height="24" width="24" :original="true"></svg-icon>
            <span class="collapse-hidden">{{ routeName }}</span>
        </a>
        <slot></slot>
    </router-link>
</template>

<script>
    export default {
        name: 'nested-nav-item',
        props: ['routeName', 'iconName', 'hasWaves'],
        computed: {
            hasSlot() {
                return !!this.$slots.default
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .nav-item {
        text-transform: uppercase;
        list-style: none;
        margin-bottom: 5px;
        .nav-link {
            color: $color-title;
            font-weight: 200;
            padding: 8px 35px 8px 15px;
            display: block;
            white-space: nowrap;
            letter-spacing: 2px;
            .svg-icon {
                margin-right: 10px;
                .svg-fill {  fill: $color-title  }
                .svg-stroke {  stroke: $color-title  }
            }
            &.has-arrow {
                position: relative;
                &::after {
                    position: absolute;
                    content: '';
                    width: 7px;
                    height: 7px;
                    border-width: 1px 0 0 1px;
                    border-style: solid;
                    border-color: $color-title;
                    right: 1em;
                    -webkit-transform: rotate(135deg) translate(0, -50%);
                    -ms-transform: rotate(135deg) translate(0, -50%);
                    -o-transform: rotate(135deg) translate(0, -50%);
                    transform: rotate(135deg) translate(0, -50%);
                    -webkit-transform-origin: top;
                    -ms-transform-origin: top;
                    -o-transform-origin: top;
                    transform-origin: top;
                    top: 47%;
                    -webkit-transition: all .3s ease-out;
                    -o-transition: all .3s ease-out;
                    transition: all .3s ease-out;
                }
            }
        }
        &.active, &:hover {
            >.nav-link {  color: $color-theme;  }
            .svg-icon {
                .svg-fill {  fill: $color-theme;  }
                .svg-stroke {  stroke: $color-theme;  }
            }
            .has-arrow::after {  border-color: $color-theme;  }
        }
        &.active {
            font-weight: 500;
            .nav-link.has-arrow::after {
                -webkit-transform: rotate(-135deg) translate(0, -50%);
                -ms-transform: rotate(-135deg) translate(0, -50%);
                -o-transform: rotate(-135deg) translate(0, -50%);
                top: 45%;
                width: 7px;
                transform: rotate(-135deg) translate(0, -50%);
            }
            .nav-nest.collapse {
                display: block;
            }
        }
    }
    .nav-nest.nest-0 > .nav-item {
        border-left: 3px solid transparent;
        &.active {
            border-left: 3px solid $color-theme;
            >.nav-link {  font-weight: 500;  }
        }
    }
</style>