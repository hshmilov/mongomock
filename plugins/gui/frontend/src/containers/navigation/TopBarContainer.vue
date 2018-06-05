<template>
    <header class="x-top-bar" :class="{ 'minimize': collapseSidebar || ($resize && $mq.below(1200)) }">
        <div class="bar-toggle">
            <a class="toggle-link" @click="toggleSidebar">
                <svg-icon name="navigation/menu" :original="true" height="20"/>
            </a>
        </div>
        <div class="bar-logo">
            <svg-icon name="logo/logo" height="30" :original="true" />
            <svg-icon name="logo/axonius" height="16" :original="true" class="logo-text"/>
        </div>
        <ul class="bar-nav">
            <li class="nav-item" v-if="runningResearch">
                <svg-icon name="symbol/running" :original="true" height="20" class="rotating"/>
            </li>
            <li class="nav-item">
                <a v-if="!runningResearch" v-tooltip.bottom="'Discover Now'" @click="startResearchNow" class="item-link">
                    <svg-icon name="action/run" :original="true" height="20"/>
                </a>
                <a v-if="runningResearch" v-tooltip.bottom="'Stop Discovery'" @click="stopResearchNow" class="item-link">
                    <svg-icon name="action/stop" :original="true" height="20"/>
                </a>
            </li>
            <li class="nav-item">
                <a class="item-link">
                    <notification-peek-container />
                </a>
            </li>
            <li class="nav-item">
                <a class="item-link" @click="navigateSettings">
                    <svg-icon name="navigation/settings" :original="true" height="20" />
                </a>
                <x-tip-info content="In order to send alerts through mail, define the server under settings"
                           v-if="mailSettingsTip" @dismiss="mailSettingsTip = false" />
                <x-tip-info content="In order to send alerts through a syslog system, define the server under settings"
                           v-if="syslogSettingsTip" @dismiss="syslogSettingsTip = false" />
            </li>
            <li class="nav-item">
                <a @click="startTour" class="item-link">
                    <svg-icon name="action/help" :original="true" height="20" />
                </a>
                <x-tip-info content="You can always start the tour again here"
                            v-if="activateTourTip" @dismiss="activateTourTip = false" />
            </li>
        </ul>
    </header>
</template>

<script>
	import NotificationPeekContainer from '../notification/NotificationPeekContainer.vue'
    import xTipInfo from '../../components/onboard/TipInfo.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_LIFECYCLE } from '../../store/modules/dashboard'
    import { UPDATE_EMPTY_STATE, START_TOUR } from '../../store/modules/onboarding'
	import { TOGGLE_SIDEBAR } from '../../store/mutations'
    import { START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '../../store/actions'

	export default {
		components: { NotificationPeekContainer, xTipInfo },
		name: 'top-bar-container',
		computed: {
            ...mapState({
                collapseSidebar(state) {
                	return state.interaction.collapseSidebar
                },
                emptyStates(state) {
                	return state.onboarding.emptyStates
                },
                lifecycle(state) {
                    return state.dashboard.lifecycle.data.subPhases || []
                },
				emptyStates(state) {
					return state.onboarding.emptyStates
				},
				tourActive(state) {
                	return state.onboarding.tourStates.active
				}
            }),
            mailSettingsTip: {
            	get() {
            		return this.emptyStates.mailSettings
                },
                set(value) {
					this.updateEmptyState({ mailSettings: value })
                }
            },
			syslogSettingsTip: {
				get() {
					return this.emptyStates.syslogSettings
				},
				set(value) {
					this.updateEmptyState({ syslogSettings: value })
				}
			}
        },
        data() {
			return {
                isDown: false,
                runningResearch: false,
                activateTourTip: false
			}
        },
        watch: {
			tourActive(isActiveNow) {
				if (!isActiveNow) {
					this.activateTourTip = true
                }
            }
        },
		methods: {
			...mapMutations({
                toggleSidebar: TOGGLE_SIDEBAR, updateEmptyState: UPDATE_EMPTY_STATE, startTour: START_TOUR }),
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
            navigateSettings() {
				if (this.mailSettingsTip || this.syslogSettingsTip) {
					this.$router.push({path: '/settings#global-settings-tab'})
                    this.mailSettingsTip = false
                    this.syslogSettingsTip = false
                } else {
				    this.$router.push({name: 'Settings'})
                }
            }
		},
		created () {
			const updateLifecycle = () => {
				this.fetchLifecycle().then(() => {
					this.runningResearch = this.lifecycle.reduce(
						(sum, item) => sum + item.status, 0) !== this.lifecycle.length
                    this.timer = setTimeout(updateLifecycle, 3000)
				})
            }
            updateLifecycle()
		},
        beforeDestroy() {
			clearTimeout(this.timer)
        }
	}
</script>

<style lang="scss">
    .x-top-bar {
        background: $grey-1;
        position: fixed;
        top: 0;
        width: 100%;
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
                position: relative;
                .svg-stroke {
                    stroke: $theme-orange;
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