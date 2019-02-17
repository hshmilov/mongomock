<template>
    <div class="x-stack" :class="{ active: Stack.active }">
        <slot />
    </div>
</template>

<script>
    export default {
        name: 'x-stack',
        data() {
            return {
                Stack: {
                    active: false
                }
            }
        },
        provide () {
            return {
                Stack: this.Stack
            }
        }
    }
</script>

<style lang="scss">
    .x-stack {
        position: relative;
        height: 100%;
        overflow: hidden;
    }
</style>