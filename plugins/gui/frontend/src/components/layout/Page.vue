<template>
    <div class="x-page" :class="{ collapse: interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <div v-if="title || breadcrumbs" class="x-header">
            <h4 class="x-title" v-if="title">{{ title }}</h4>
            <h4 class="x-title" v-else>
                <!-- Adding title for each breadcrumb, linked to the page, except last one which is the viewed page -->
                <template v-for="breadcrumb in breadcrumbs.splice(0, breadcrumbs.length - 1)">
                    <router-link :to="breadcrumb.path" active-class="" class="x-crumb">{{ breadcrumb.title }}</router-link>
                </template>
                <!-- Adding currently viewed page without a link -->
                {{breadcrumbs[breadcrumbs.length - 1].title}}
            </h4>
            <div class="x-action"><slot name="pageAction"/></div>
        </div>
        <div class="x-body">
            <slot/>
        </div>
    </div>
</template>

<script>
	import { mapState } from 'vuex'

	export default {
		name: 'x-page',
		props: ['title', 'breadcrumbs'],
		computed: mapState(['interaction']),
	}
</script>

<style lang="scss">
    .x-page {
        display: flex;
        flex-direction: column;
        background: $grey-1;
        padding: 72px 24px 24px 264px;
        position: relative;
        width: 100%;
        height: 100vh;
        &.collapse {
            display: flex;
            flex-direction: column;
            padding: 72px 24px 24px 84px;
        }
        > .x-header {
            display: flex;
            width: 100%;
            text-transform: capitalize;
            z-index: 100;
            color: $theme-black;
            margin-bottom: 24px;
            padding: 12px 8px;
            border-top: 1px solid;
            border-bottom: 1px solid;
            border-color: rgba($theme-orange, 0.2);
            .x-title {
                flex: 1 0 auto;
                font-weight: 200;
                letter-spacing: 1px;
                margin-bottom: 0;
                vertical-align: middle;
                line-height: 24px;
                display: inline-block;
                .x-crumb {
                    position: relative;
                    margin-right: 18px;
                    &:after {
                        right: -12px;
                        @include triangle('right', $color: $theme-black);
                    }
                }
            }
            .x-action {
                vertical-align: middle;
                line-height: 24px;
                font-size: 12px;
                text-transform: none;
                color: $theme-blue;
                &:hover {
                    color: $theme-orange;
                }
            }
        }
        .x-body {
            flex: 1 0 auto;
            padding: 0;
            height: calc(100vh - 172px);
            overflow: auto;
        }
    }
</style>