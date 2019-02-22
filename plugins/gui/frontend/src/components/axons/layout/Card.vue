<template>
    <div class="x-card">
        <div class="header">
            <x-button link v-if="reversible" class="back" @click="$emit('back')">&lt;</x-button>
            <template v-if="logo">
                <x-title :logo="logo">{{title}}</x-title>
            </template>
            <div class="title" :title="title" v-else>{{title}}</div>
            <x-button link v-if="removable" class="remove" @click="$emit('remove')">x</x-button>
        </div>
        <slot></slot>
    </div>
</template>

<script>
    import xTitle from './Title.vue'
    import xButton from '../inputs/Button.vue'

    export default {
        name: 'x-card',
        components: {
            xTitle, xButton
        },
        props: {
            title: {required: true},
            logo: {},
            removable: {
                type: Boolean,
                default: false
            },
            reversible: {
                type: Boolean,
                default: false
            }
        }
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

        > .header {
            display: flex;
            width: 100%;
            margin-bottom: 12px;

            .back {
                font-size: 24px;
            }

            >.x-title {
                width: calc(100% - 36px);
                .md-image {
                    height: 48px;
                }
                .text {
                    font-size: 24px;
                    margin-left: 24px;
                    text-overflow: ellipsis;
                    width: calc(100% - 84px);
                    overflow-x: hidden;
                    line-height: 48px;
                }
            }

            > .title {
                flex: 1 0 auto;
                font-size: 16px;
                width: 280px;
                text-overflow: ellipsis;
                white-space: nowrap;
                overflow: hidden;
            }

            .remove {
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