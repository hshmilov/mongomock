<template>
    <div class="dropdown" v-bind:class="{ 'show': openDropdown }" v-on-clickaway="closeDropdown">
        <div class="dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" :aria-expanded="`${openDropdown}`"
            @click="done = false; openDropdown = !openDropdown">
            <slot name="dropdownTrigger"></slot>
        </div>
        <div :class="`dropdown-menu ${animateClass || ''} ${menuClass || ''}`">
            <slot v-if="!done" name="dropdownContent" :onDone="handleDone"></slot>
            <div v-if="done" class="dropdown-success animated fadeIn">
                <div>{{successMessage}}</div>
                <i class="icon-checkmark2"></i>
            </div>
        </div>
    </div>
</template>

<script>
    import { mixin as clickaway } from 'vue-clickaway'

    export default {
        name: 'dropdown-menu',
        mixins: [ clickaway ],
        props: [ 'animateClass', 'menuClass' ],
        data() {
            return {
                openDropdown: false,
                done: false,
                successMessage: ''
            }
        },
        methods: {
            closeDropdown() {
                this.openDropdown = false
            },
            handleDone(success, successMessage) {
            	if (success) {
            		this.done = true
					this.successMessage = successMessage
        			setTimeout(() => {
						this.closeDropdown()
					}, 1000)
				}
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .dropdown {
        .dropdown-menu {
            z-index: 10;
            top: 96%;
            width: 100%;
            box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
            -webkit-box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
            -moz-box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
            border-color: $border-color;
            padding: 12px;
            &.w-xl {
                width: 600px;
            }
            &.w-lg {
                width: 480px;
            }
            &.w-md {
                width: 360px;
            }
            &.w-sm {
                width: 240px;
            }
            &.right {
                right: 0;
                left: auto;
            }
            .checkbox {
                margin-top: 8px;
                width: 100%;
                &:first-of-type {
                    margin-top: 0;
                }
            }
            .dropdown-success {
                color: $color-success;
                text-align: center;
                i {
                    font-size: 64px;
                }
            }
        }
        .dropdown-toggle {
            cursor: pointer;
            font-size: 80%;
            padding-right: 4px;
            padding-left: 4px;
            i, .svg-icon {
                height: 24px;
                margin-top: 2px;
                font-size: 18px;
                vertical-align: middle;
                line-height: 28px;
            }
            &:after {
                position: absolute;
                margin: 6px 12px;
                top: 0;
                right: 0;
                width: 12px;
                height: 12px;
                border-top: 1px solid;
                border-left: 1px solid;
                border-right: 0;
                transform: rotate(225deg);
                transition: transform 0.2s;
            }
        }
        .scale-up {
            -webkit-transition: all 0.3s ease;
            transition: all 0.3s ease;
            -webkit-transform: scale(0);
            transform: scale(0);
            transform-origin: center 0px;
            display: inline-block;
            &.right {
                transform-origin: right 0px;
            }
        }
        &.show>.scale-up {
            transform: scale(1);
        }
    }
    .show .dropdown-toggle:after {
        transform: rotate(45deg);
        margin: 12px 12px;
    }
</style>