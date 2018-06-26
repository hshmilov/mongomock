<template>
    <div class="x-card">
        <div class="x-header">
            <div class="x-title" :title="title">{{title}}</div>
            <div v-if="removable" class="x-remove" @click="$emit('remove')">x</div>
        </div>
        <slot></slot>
    </div>
</template>

<script>
    export default {
        name: 'x-card',
        props: {title: {required: true}, removable: {default: false}},
    }
</script>

<style lang="scss">
    .x-card {
        display: flex;
        flex-direction: column;
        background-color: white;
        box-shadow: 0 2px 12px 0px rgba(0, 0, 0, 0.2);
        padding: 12px;
        border-radius: 2px;
        > .x-header {
            flex: 0 1 auto;
            display: flex;
            margin-bottom: 12px;
            > .x-title {
                flex: 1 0 auto;
                font-size: 16px;
                width: 280px;
                text-overflow: ellipsis;
                white-space: nowrap;
                overflow: hidden;
            }
            .x-remove {
                padding: 0 4px;
                margin-right: -2px;
                line-height: 18px;
                font-size: 18px;
                align-self: center;
                &:hover {
                    cursor: pointer;
                    background-color: rgba($theme-orange, 0.6);
                    border-radius: 100%;
                }
            }
        }
    }
</style>