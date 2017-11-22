<template>
    <div class="info-dialog d-flex flex-column" v-bind:class="{ 'show animated slideInRight': open }">
        <div class="info-dialog-header p-3">
            <span class="info-dialog-close" @click="closeDialog($event)">x</span>
            <div class="info-dialog-title">{{ title }}</div>
        </div>
        <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
            <slot></slot>
        </vue-scrollbar>
    </div>
</template>

<script>
    import VueScrollbar from 'vue2-scrollbar'

    export default {
        name: 'info-dialog',
      components: { VueScrollbar },
        props: ['open', 'title', 'closeDialog']
    }
</script>

<style lang="scss">
    @import '../scss/config';

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
        width: 0;
        box-shadow: -4px 0px 4px rgba(0, 0, 0, 0.5);
        &.show {
            width: 280px;
	    }
        .info-dialog-header {
            background-color: $color-theme;
            height: 80px;
            color: $color-light;
            position: relative;
            font-size: 110%;
            .info-dialog-close {
                cursor: pointer;
                float: right;
                line-height: 12px;
            }
            .info-dialog-title {
                bottom: 0;
                position: absolute;
                vertical-align: bottom;
            }
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
            color: $color-yellow;
        }
        .btn {
            position: absolute;
            bottom: 0;
            width: 100%;
            border-radius: 0;
            background-color: $color-theme;
            color: $color-light !important;
            &:hover {
                -webkit-box-shadow: 4px -2px 12px 4px rgba($color-theme, 0.42), 23px 4px 0 0 rgba(0, 0, 0, 0.12), 10px 8px 0 -5px rgba($color-theme, 0.2);
                box-shadow: 4px -2px 12px 4px rgba($color-theme, 0.42), 23px 4px 0 0 rgba(0, 0, 0, 0.12), 10px 8px 0 -5px rgba($color-theme, 0.2);
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
