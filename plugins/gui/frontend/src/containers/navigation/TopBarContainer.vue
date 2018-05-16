<template>
    <header class="x-top-bar" v-bind:class="{ 'minimize': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <div class="bar-toggle">
            <a class="toggle-link" v-on:click="toggleSidebar">
                <svg-icon name="navigation/menu" :original="true" height="20"/>
            </a>
        </div>
        <div class="bar-logo">
            <svg-icon name="logo/logo" height="30" :original="true" />
            <svg-icon name="logo/axonius" height="16" :original="true" class="logo-text"/>
        </div>
        <ul class="bar-nav">
            <li class="nav-item">
                <template v-if="runningResearch">
                    <svg-icon name="action/lifecycle/running" :original="true" height="20" class="rotating"/>
                </template>
            </li>
            <li class="nav-item">
                <a v-if="!runningResearch" v-tooltip.bottom="'Discover Now'" @click="startResearchNow" class="item-link">
                    <svg-icon name="action/lifecycle/run" :original="true" height="20"/>
                </a>
                <a v-if="runningResearch" v-tooltip.bottom="'Stop Discovery'" @click="stopResearchNow" class="item-link">
                    <svg-icon name="action/lifecycle/stop" :original="true" height="20"/>
                </a>
            </li>
            <li class="nav-item">
                <a class="item-link">
                    <notification-peek-container />
                </a>
            </li>
            <li class="nav-item">
                <router-link :to="{ name: 'Settings' }" class="item-link" tag="a">
                    <svg-icon name="navigation/settings" :original="true" height="20" />
                </router-link>
            </li>
        </ul>
    </header>
</template>

<script>
	import NotificationPeekContainer from '../notification/NotificationPeekContainer.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_LIFECYCLE } from '../../store/modules/dashboard'
	import { TOGGLE_SIDEBAR } from '../../store/mutations'
    import { START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '../../store/actions'

	export default {
		components: { NotificationPeekContainer },
		name: 'top-bar-container',
		computed: {
            ...mapState(['interaction', 'dashboard']),
            lifecycle () {
                if (!this.dashboard.lifecycle.data.subPhases) return []

                return this.dashboard.lifecycle.data.subPhases
            }
        },
        data() {
			return {
                isDown: false,
                runningResearch: false
			}
        },
		methods: {
			...mapMutations({toggleSidebar: TOGGLE_SIDEBAR}),
			...mapActions({
                fetchLifecycle: FETCH_LIFECYCLE,
                startResearch: START_RESEARCH_PHASE,
                stopResearch: STOP_RESEARCH_PHASE,

			}),
            startResearchNow() {
                this.runningResearch = true
                this.startResearch()
            },
            stopResearchNow() {
                this.runningResearch = false
                this.stopResearch()
            },
            updateLifecycle() {
				this.fetchLifecycle().then(() => {
					this.runningResearch = this.lifecycle.reduce(
						(sum, item) => sum + item.status, 0) !== this.lifecycle.length
				})
            }
		},
		created () {
            this.updateLifecycle()
            this.interval = setInterval(function () {
                this.updateLifecycle()
            }.bind(this), 10000)
		},
		beforeDestroy () {
            clearInterval(this.interval)
		}
	}
</script>

<style lang="scss">
    .x-top-bar {
        background: $grey-1;
        position: relative;
        z-index: 101;
        display: flex;
        height: 60px;
        .bar-toggle {
            line-height: 60px;
            width: 240px;
            text-align: left;
            background-color: $theme-black;
            transition: all ease-in 0.2s;
            .toggle-link {
                padding: 0 18px;
                .svg-stroke {
                    stroke: $grey-4;
                }
                .svg-fill {
                    fill: $grey-4;
                }
                &:hover {
                    .svg-stroke {
                        stroke: $theme-orange;
                    }
                    .svg-fill {
                        fill: $theme-orange;
                    }
                }
            }
        }
        .bar-logo {
            margin-left: 24px;
            line-height: 60px;
        }
        .bar-nav {
            flex: 1 0 auto;
            display: flex;
            justify-content: flex-end;
            list-style: none;
            margin-right: 12px;
            > .nav-item {
                margin: 0 12px;
                line-height: 60px;
                .svg-stroke {
                    fill: $theme-orange;
                }
                .svg-fill {
                    fill: $theme-orange;
                }
                .item-link {
                    .svg-fill {
                        fill: $theme-black;
                    }
                    .svg-stroke {
                        stroke: $theme-black;
                    }
                    .svg-bg {
                        fill: $grey-1;
                    }
                    &:hover {
                        .svg-stroke {
                            stroke: $theme-orange;
                        }
                        .svg-fill {
                            fill: $theme-orange;
                        }
                    }
                }
            }
        }
    }

    .x-top-bar.minimize {
        .bar-toggle {
            width: 60px;
        }
    }

    .tooltip {
        display: block !important;
        z-index: 10000;
    }

    .tooltip .tooltip-inner {
        background: $theme-black;
        color: $theme-orange;
        border-radius: 16px;
        padding: 5px 10px 4px;
    }

    .tooltip .tooltip-arrow {
        width: 0;
        height: 0;
        border-style: solid;
        position: absolute;
        margin: 5px;
        border-color: $theme-black;
    }

    .tooltip[x-placement^="bottom"] {
        margin-top: 5px;
    }

    .tooltip[x-placement^="bottom"] .tooltip-arrow {
        border-width: 0 5px 5px 5px;
        border-left-color: transparent !important;
        border-right-color: transparent !important;
        border-top-color: transparent !important;
        top: -5px;
        left: calc(50% - 5px);
        margin-top: 0;
        margin-bottom: 0;
    }


    .tooltip[aria-hidden='true'] {
        visibility: hidden;
        opacity: 0;
        transition: opacity .15s, visibility .15s;
    }

    .tooltip[aria-hidden='false'] {
        visibility: visible;
        opacity: 1;
        transition: opacity .15s;
    }

</style>