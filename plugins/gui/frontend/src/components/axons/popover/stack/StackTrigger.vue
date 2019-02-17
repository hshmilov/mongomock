<template>
    <div class="x-stack-trigger" @click="toggleStack">
        <slot />
    </div>
</template>

<script>
    export default {
        name: 'x-stack-trigger',
        inject: ['Stack'],
        methods: {
            toggleStack() {
                this.Stack.active = !this.Stack.active
                this.$emit('click')
            }
        }
    }
</script>

<style lang="scss">
    .x-stack-trigger {
        position: relative;
        z-index: 200;
    }
</style>