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
            <li class="nav-item">
                <a v-if="research.starting" class="item-link research-link disabled">
                    <svg-icon name="symbol/running" class="rotating" :original="true" height="20" />
                    <div>Initiating...</div>
                </a>
                <a v-else-if="research.stopping" @click="stopResearchNow" class="item-link research-link disabled">
                    <svg-icon name="symbol/running" class="rotating" :original="true" height="20" />
                    <div>Stopping...</div>
                </a>
                <a v-else-if="!research.running" @click="startResearchNow" class="item-link research-link" id="run_research">
                    <svg-icon name="action/start" :original="true" height="20" />
                    <div>Discover Now</div>
                </a>
                <a v-else-if="research.running" @click="stopResearchNow" class="item-link research-link" id="stop_research">
                    <svg-icon name="action/stop" :original="true" height="20" />
                    <div>Stop Discovery</div>
                </a>
            </li>
            <li class="nav-item">
                <a class="item-link">
                    <notification-peek-container />
                </a>
            </li>
            <li class="nav-item">
                <a class="item-link" @click="navigateSettings" id="settings">
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
                phasesStatus(state) {
                    return state.dashboard.lifecycle.data.subPhases || []
                },
                researchStatus(state) {
                    return state.dashboard.lifecycle.data.status || {}
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
			},
            enableResearchStart() {
                return (!this.research.running && !this.research.starting) || this.research.stopping
            }
        },
        data() {
			return {
                isDown: false,
                research: {
                    running: false,
                    stopping: false,
                    starting: false
                },
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
                this.research.starting = true
                this.startResearch().catch(() => this.research.starting = false )
            },
            stopResearchNow() {
                this.research.stopping = true
                this.stopResearch().catch(() => this.research.stopping = false )
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
					if (this._isDestroyed) return
					this.research.running = this.phasesStatus.reduce(
						(sum, item) => sum + item.status, 0) !== this.phasesStatus.length
                    this.research.stopping = this.researchStatus.stopping
                    this.research.starting = this.researchStatus.starting
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
        background: $grey-0;
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
                margin: auto 12px;
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
                    &:hover {
                        .svg-stroke {
                            stroke: $theme-orange;
                        }
                        .svg-fill {
                            fill: $theme-orange;
                        }
                    }
                    &.research-link {
                        background: $theme-black;
                        color: $grey-1;
                        border-radius: 16px;
                        display: flex;
                        align-items: center;
                        padding: 0 12px;
                        line-height: 32px;
                        width: 136px;
                        .svg-fill {
                            fill: $grey-1;
                            margin-right: 8px;
                        }
                        &:hover .svg-fill, .rotating .svg-fill {
                            fill: $theme-orange;
                        }
                        .svg-stroke {
                            stroke: $theme-orange;
                        }
                    }
                    &.disabled {
                        cursor: default;
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

</style>