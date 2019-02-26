<template>
    <div class="x-page" :class="{ collapse: collapseSidebar }">
        <div v-if="title || breadcrumbs" class="header">
            <template v-if="title">
                <h4 class="title">{{ title }}</h4>
                <md-chip v-if="beta">BETA</md-chip>
            </template>
            <h4 class="title" v-else>
                <!-- Adding title for each breadcrumb, linked to the page, except last one which is the viewed page -->
                <div v-for="(breadcrumb, i) in breadcrumbs.slice(0, breadcrumbs.length - 1)" class="crumb">
                    <router-link :to="breadcrumb.path" active-class="">{{ breadcrumb.title }}</router-link>
                    <md-chip v-if="beta && !i">BETA</md-chip>
                </div>
                <!-- Adding currently viewed page without a link -->
                <span>{{breadcrumbs[breadcrumbs.length - 1].title}}</span>
            </h4>
            <div class="action print-exclude">
                <slot name="action"/>
            </div>
        </div>
        <div class="x-body">
            <slot/>
        </div>
    </div>
</template>

<script>
    import {mapState} from 'vuex'

    export default {
        name: 'x-page',
        props: {
            title: String,
            breadcrumbs: Array,
            beta: {
                type: Boolean,
                default: false
            }
        },
        computed: mapState({
            collapseSidebar(state) {
                return state.interaction.collapseSidebar
            }
        })
    }
</script>

<style lang="scss">
    .x-page {
        display: flex;
        flex-direction: column;
        background: $grey-0;
        padding: 12px 24px 24px 264px;
        position: relative;
        margin-top: 60px;
        width: 100vw;
        height: calc(100vh - 60px);

        &.collapse {
            display: flex;
            flex-direction: column;
            padding-left: 84px;
        }

        > .header {
            display: flex;
            align-items: center;
            text-transform: capitalize;
            z-index: 100;
            color: $theme-black;
            margin-bottom: 12px;
            padding: 12px 8px;
            border-top: 1px solid;
            border-bottom: 1px solid;
            border-color: rgba($theme-orange, 0.2);

            .title {
                font-weight: 200;
                letter-spacing: 1px;
                margin: 0;
                vertical-align: middle;
                line-height: 30px;
                display: flex;

                .crumb {
                    position: relative;
                    margin-right: 18px;

                    &:after {
                        right: -12px;
                        @include triangle('right', $color: $theme-black);
                    }
                }
            }

            .action {
                vertical-align: middle;
                line-height: 24px;
                font-size: 12px;
                text-transform: none;
                color: $theme-blue;

                &:hover {
                    color: $theme-orange;
                }
            }

            .md-chip {
                background-color: rgba($theme-orange, 0.2);
                height: 20px;
                line-height: 20px;
                margin-left: 4px;
            }
        }

        .x-body {
            padding: 0;
            height: calc(100% - 80px);
            overflow: auto;
            position: relative;
        }
    }
</style>