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
                <i class="icon-check"></i>
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
        border: 1px solid $border-color;
        border-radius: 4px;
        .dropdown-toggle {
            cursor: pointer;
            font-size: 80%;
            padding-right: 4px;
            padding-left: 4px;
            i, img {
                height: 24px;
                margin-right: 24px;
                margin-top: 2px;
                font-size: 18px;
                vertical-align: middle;
                line-height: 28px;
            }
            &:after {
                position: absolute;
                margin-right: 8px;
                margin-top: 12px;
                top: 0;
                right: 0;
                border-top: .5em solid;
                border-right: .5em solid transparent;
                border-left: .5em solid transparent;
            }
        }
        .dropdown-menu {
            z-index: 10;
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
</style>