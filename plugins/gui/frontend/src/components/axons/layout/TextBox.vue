<template>
    <div class="x-text-box" :class="{disabled: !clickable, selected}">
        <slot name="logo" />
        <div class="content">{{ text }}</div>
        <x-button v-if="removable" link @click.prevent.stop="remove">x</x-button>
    </div>
</template>

<script>
    import xButton from '../inputs/Button.vue'

    export default {
        name: 'x-text-box',
        props: {
            text: String,
            selected: Boolean,
            clickable: {
                type: Boolean,
                default: true
            },
            removable: {
                type: Boolean,
                default: true
            }
        },
        components: {
            xButton
        },
        methods: {
            remove() {
                this.$emit('remove')
            }
        }
    }
</script>

<style lang="scss">
    .x-text-box {
        background-color: $grey-1;
        text-transform: capitalize;
        display: flex;
        align-items: center;
        position: relative;
        transition: all .4s ease-in-out;
        border-radius: 24px;
        width: 240px;
        height: 48px;
        &:not(.disabled) {
            cursor: pointer;
        }
        &:hover:not(.disabled), &.selected {
            background-color: $grey-2;
        }
        .content {
            padding-left: 12px;
            text-overflow: ellipsis;
            white-space: nowrap;
            width: calc(100% - 24px);
            overflow-x: hidden;
        }
    }
</style>