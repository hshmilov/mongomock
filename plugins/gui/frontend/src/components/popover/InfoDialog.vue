<template>
    <transition name="custom-classes-transition" :duration="800"
                enter-active-class="animated slideInRight" leave-active-class="animated slideOutRight">
        <div class="info-dialog d-flex flex-column">
            <div class="info-dialog-header p-3">
                <span class="info-dialog-close" @click="$emit('close')">x</span>
                <div class="info-dialog-title">{{ title }}</div>
            </div>
            <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
                <div class="info-dialog-body">
                    <slot></slot>
                    <div class="clearfix"></div>
                </div>
            </vue-scrollbar>
        </div>
    </transition>
</template>

<script>
    import VueScrollbar from 'vue2-scrollbar'

    export default {
        name: 'info-dialog',
        components: { VueScrollbar },
        props: ['open', 'title']
    }
</script>

<style lang="scss">
    .info-dialog {
        overflow: hidden;
        position: absolute;
        top: 0;
        right: 0px;
        background-color: $background-color-light;
        font-size: 90%;
        letter-spacing: 1.5px;
        font-weight: 200;
        height: 100%;
        box-shadow: -4px 0px 4px rgba(0, 0, 0, 0.5);
        width: 360px;
        .info-dialog-header {
            background-color: $color-theme-dark;
            height: 80px;
            line-height: 80px;
            color: $color-theme-light;
            position: relative;
            font-size: 110%;
            .info-dialog-close {
                cursor: pointer;
                float: right;
                font-size: 18px;
                line-height: 18px;
                margin: -8px;
                color: $color-btn;
                &:hover {
                    color: $color-light;
                }
            }
        }
        .info-dialog-body {
            padding: 24px;
        }
        .data-logo {
            width: 48px;
        }
        .icon-play-circle {
            font-size: 36px;
            text-align: center;
            color: $color-success;
        }
        .icon-pause-circle {
            font-size: 36px;
            text-align: center;
            color: $color-warning;
        }
        .btn {
            position: absolute;
            bottom: 0;
            width: 100%;
            border-radius: 0;
            background-color: $color-theme-light;
            color: $color-light !important;
            &:hover {
                -webkit-box-shadow: 4px -2px 12px 4px rgba($color-theme-light, 0.42), 23px 4px 0 0 rgba(0, 0, 0, 0.12), 10px 8px 0 -5px rgba($color-theme-light, 0.2);
                box-shadow: 4px -2px 12px 4px rgba($color-theme-light, 0.42), 23px 4px 0 0 rgba(0, 0, 0, 0.12), 10px 8px 0 -5px rgba($color-theme-light, 0.2);
            }
        }
    }
    @keyframes appear {
        0% {
            width: 0px;
        }
        100% {
            width: 280px;
        }
    }

</style>
