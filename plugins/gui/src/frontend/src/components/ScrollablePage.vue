<template>
    <div class="page-wrapper"
         v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <div v-if="title" class="page-header">
            <h2>{{ title }}</h2>
        </div>
        <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
            <div class="page-body">
                <slot></slot>
            </div>
        </vue-scrollbar>
    </div>
</template>

<script>
    import VueScrollbar from 'vue2-scrollbar'
    import { mapState } from 'vuex'

    export default {
        name: 'scrollable-page',
        components: { VueScrollbar },
        props: ['title'],
        computed: mapState(['interaction'])
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .page-wrapper {
        background: $background-color;
        padding: 62px 0 0;
        height: 100%;
        padding-left: 240px;
        display: flex;
        flex-flow: column;
        position: relative;
        width: 100%;
        &.collapse {
            display: block;
            padding-left: 60px;
            padding-top: 60px;
        }
        .page-header {
            flex: 0 1 auto;
            height: 36px;
            width: 100%;
            padding: 12px 24px;
            text-transform: uppercase;
            z-index: 100;
            color: $color-text-title;
            h2 {
                font-weight: 200;
                letter-spacing: 1px;
                margin-bottom: 0;
                vertical-align: middle;
                line-height: 24px;
            }
        }
        .scrollbar-container {
            flex: 1 1 auto;
            height: 100vh;
            background-color: transparent;
            margin: 0;
            .page-body {
                padding: 12px 24px;
                height: 100%;
            }
        }
    }
</style>