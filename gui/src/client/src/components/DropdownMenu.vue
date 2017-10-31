<template>
    <div class="dropdown" v-bind:class="{ 'show': openDropdown }" v-on-clickaway="closeDropdown">
        <a class="dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" :aria-expanded="`${openDropdown}`"
            @click="openDropdown = !openDropdown">
            <slot name="dropdownTrigger"></slot>
        </a>
        <div class="dropdown-menu dropdown-menu-right scale-up"
             v-bind:class="{ 'show': openDropdown, 'right': positionRight }">
            <slot name="dropdownContent"></slot>
        </div>
    </div>
</template>

<script>
    import { mixin as clickaway } from 'vue-clickaway'

    export default {
        name: 'dropdown-menu',
        mixins: [ clickaway ],
        props: [ 'positionRight' ],
        data() {
            return {
                openDropdown: false
            }
        },
        methods: {
            closeDropdown() {
                this.openDropdown = false
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .dropdown {
        border: 1px solid $border-color;
        border-radius: 4px;
        &:hover, &.show {
            background-color: rgba(235, 233, 250, 0.6);
            border-color: $color-theme;
        }
        .dropdown-toggle {
            font-size: 80%;
            padding-right: 4px;
            padding-left: 4px;
            i {
                margin-right: 12px;
                font-size: 18px;
                vertical-align: middle;
                line-height: 25px;
            }
        }
        .dropdown-menu {
            top: 96%;
            box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
            -webkit-box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
            -moz-box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
            border-color: $border-color;
            padding: 12px;
            &.right {
                right: 0;
                left: auto;
            }
        }
        .scale-up {
            -webkit-transition: all 0.3s ease;
            transition: all 0.3s ease;
            -webkit-transform: scale(0);
            transform: scale(0);
            display: inline-block;
            transform-origin: right 0px;
            &.show {
                transform: scale(1);
                transform-origin: right 0px;
            }
        }

    }
</style>