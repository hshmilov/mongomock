<template>
    <div class="x-tip-info">
        <div class="content">{{content}}</div>
        <x-button-dismiss @click.native="$emit('dismiss')"/>
    </div>
</template>

<script>
    import xButtonDismiss from './ButtonDismiss.vue'

    export default {
        name: 'x-tip-info',
        components: {xButtonDismiss},
        props: {content: {required: true}}
    }
</script>

<style lang="scss">
    .x-tip-info {
        position: absolute;
        background-color: $theme-white;
        box-shadow: 1px 0 6px 0 rgba(0, 0, 0, 0.2);
        padding: 12px;
        border-radius: 4px;
        right: -6px;
        animation: bounceY 1s ease;
        line-height: 24px;

        &:before {
            content: '';
            position: absolute;
            height: 8px;
            width: 8px;
            top: -4px;
            right: 12px;
            box-shadow: 1px 0 6px 0 rgba(0, 0, 0, 0.2);
            transform: rotate(45deg);
            background-color: $theme-white;
        }

        &:after {
            content: '';
            position: absolute;
            height: 8px;
            width: 16px;
            top: 0;
            right: 8px;
            background-color: $theme-white;
        }

        .content {
            width: 200px;
            white-space: pre-wrap;
        }

        .link {
            text-align: right;
        }
    }
</style>