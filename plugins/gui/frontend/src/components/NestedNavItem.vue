<template>
    <router-link tag="li" :to="!disabled? { name: routeName, path: routerPath }: {}" class="nav-item"
                 :active-class="(!disabled && !exact)? 'active': ''"
                 :exact-active-class="(!disabled && exact)? 'active': ''">
        <a class="nav-link" v-bind:class="{ 'has-arrow': hasSlot }" :title="routeName">
            <svg-icon v-if="iconName" :name="`navigation/${iconName}`" height="24" width="24" :original="true"/>
            <span>{{ routeName }}</span>
        </a>
        <slot/>
    </router-link>
</template>

<script>
    export default {
        name: 'nested-nav-item',
        props: ['routeName', 'routerPath', 'iconName', 'exact', 'disabled'],
        computed: {
            hasSlot() {
                return !!this.$slots.default
            }
        }
    }
</script>

<style lang="scss">
    .nav-item {
        text-transform: capitalize;
        list-style: none;
        margin-bottom: 5px;
        .nav-link {
            color: $color-btn;
            font-weight: 200;
            padding: 8px 35px 8px 15px;
            display: block;
            white-space: nowrap;
            letter-spacing: 2px;
            .svg-icon {
                margin-right: 10px;
                .svg-fill {  fill: $color-btn  }
                .svg-stroke {  stroke: $color-btn  }
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
                    border-color: $color-text-main;
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
        &:hover {
            >.nav-link {  color: $color-btn-hover;  }
            .svg-icon {
                .svg-fill {  fill: $color-btn-hover;  }
                .svg-stroke {  stroke: $color-btn-hover;  }
            }
            .has-arrow::after {  border-color: $color-btn-hover;  }
        }
        &.active {
            >.nav-link {  color: $color-theme-light;  }
            .svg-icon {
                .svg-fill {  fill: $color-theme-light;  }
                .svg-stroke {  stroke: $color-theme-light;  }
            }
            .has-arrow::after {  border-color: $color-theme-light;  }
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
            border-left: 3px solid $color-theme-light;
        }
    }
</style>