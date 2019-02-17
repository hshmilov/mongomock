<template>
    <x-box class="x-split-box">
        <div class="main">
            <slot name="main" />
        </div>
        <div class="details">
            <transition name="slide-fade" mode="out-in">
                <slot name="details" />
            </transition>
        </div>
    </x-box>
</template>

<script>
    import xBox from './Box.vue'

    export default {
        name: 'x-split-box',
        components: {
            xBox
        }
    }
</script>

<style lang="scss">
    .x-split-box {
        height: 100%;
        display: flex;
        overflow: hidden;
        > .main {
            height: 100%;
            width: 600px;
            padding: 12px;
            margin-right: 12px;
        }
        .details {
            height: 100%;
            width: calc(100% - 600px);
            .slide-fade-enter-active {
                transition: all .6s cubic-bezier(1.0, 0.4, 0.8, 1.0);
            }
            .slide-fade-leave-active {
                transition: all .2s ease;
            }
            .slide-fade-enter, .slide-fade-leave-to {
                transform: translateX(50%);
                opacity: 0;
            }
        }
    }
</style>