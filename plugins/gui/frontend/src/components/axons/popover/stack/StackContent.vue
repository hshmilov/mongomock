<template>
    <div class="x-stack-content">
        <transition name="slide-fade" mode="out-in">
            <transition-group v-if="Stack.active" name="list" tag="div" class="content open" key="open">
                <slot />
            </transition-group>
            <transition-group v-else name="list" tag="div" class="content closed" key="closed">
                <slot />
            </transition-group>
        </transition>
    </div>
</template>

<script>
    export default {
        name: 'x-stack-content',
        inject: ['Stack']
    }
</script>

<style lang="scss">
    .x-stack-content {
        > .content {
            display: grid;
            align-items: end;
            z-index: 100;
            &.closed {
                grid-auto-rows: 36px;
                opacity: 0.4;
                &.slide-fade-enter, &.slide-fade-leave-to {
                    transform: translateY(-100%);
                }
                &.slide-fade-enter-active, &.slide-fade-leave-active {
                    transition: all .4s ease-in-out;
                }
            }
            &.open {
                grid-auto-rows: auto;
                grid-gap: 8px 0;
                opacity: 1;
                &.slide-fade-enter, &.slide-fade-leave-to {
                    transform: translateY(-100%);
                    opacity: 0.4;
                }
                &.slide-fade-enter-active, &.slide-fade-leave-active {
                    transition: all .6s ease-in-out;
                }
            }
            .list-enter-active, .list-leave-active {
                transition: all .4s;
            }
            .list-enter, .list-leave-to {
                opacity: 0;
                transform: translateY(-12px);
            }
        }
    }
</style>