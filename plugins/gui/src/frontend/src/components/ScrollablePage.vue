<template>
    <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
        <div class="page-wrapper"
             v-bind:class=" { 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
            <div v-if="title || breadcrumbs" class="page-header">
                <h2 v-if="title">{{ title }}</h2>
                <h2 v-else>
                    <!-- Adding title for each breadcrumb, linked to the page, except last one which is the viewed page -->
                    <span v-for="breadcrumb in breadcrumbs.splice(0, breadcrumbs.length - 1)">
                        <router-link :to="breadcrumb.path" active-class="">{{ breadcrumb.title }}</router-link> &gt; </span>
                    <!-- Adding currently viewed page without a link -->
                    {{breadcrumbs[breadcrumbs.length - 1].title}}
                </h2>
                <slot name="pageAction"></slot>
            </div>
            <div class="page-body">
                <slot></slot>
            </div>
            <div class="clearfix"></div>
        </div>
    </vue-scrollbar>
</template>

<script>
	import VueScrollbar from 'vue2-scrollbar'
	import { mapState } from 'vuex'

	export default {
		name: 'scrollable-page',
		components: {VueScrollbar},
		props: ['title', 'breadcrumbs'],
		computed: mapState(['interaction']),
        mounted() {
			window.addEventListener('keyup', (event) => {
				if (event.keyCode === 40) {
					this.$refs.Scrollbar.scrollToY(this.$refs.Scrollbar.top + 80)
				} else if (event.keyCode === 38) {
					this.$refs.Scrollbar.scrollToY(this.$refs.Scrollbar.top - 80)
				}
			})
        }
	}
</script>

<style lang="scss">
    @import '../scss/config';

    .page-wrapper {
        background: $background-color;
        padding: 62px 0 0;
        height: 100%;
        padding-left: 240px;
        position: relative;
        width: 100%;
        &.collapse {
            display: block;
            padding-left: 60px;
            padding-top: 60px;
        }
        .page-header {
            display: flex;
            height: 36px;
            width: 100%;
            padding: 12px 24px;
            text-transform: uppercase;
            z-index: 100;
            color: $color-text-title;
            h2 {
                flex: 1 0 auto;
                font-weight: 200;
                letter-spacing: 1px;
                margin-bottom: 0;
                vertical-align: middle;
                line-height: 24px;
                display: inline-block;
            }
            .action {
                float: right;
                font-size: 12px;
                text-transform: none;
                color: $color-info;
                &:hover {
                    color: $color-theme-light;
                }
            }
        }
        .page-body {
            padding: 12px 24px;
            height: 100%;
        }
    }
</style>