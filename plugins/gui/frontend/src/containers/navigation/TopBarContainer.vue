<template>
    <header class="topbar" v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <nav class="navbar top-navbar navbar-expand navbar-light">
            <div class="navbar-header">
                <a class="nav-link sidebartoggler hidden-sm-down" v-on:click="toggleSidebar">
                    <svg-icon name="navigation/menu" :original="true" height="20"/>
                </a>
            </div>
            <div class="navbar-collapse">
                <div class="navbar-logo">
                    <svg-icon name="logo/logo" height="30" :original="true" />
                    <svg-icon name="logo/axonius" height="16" :original="true" class="logo-text"/>
                </div>
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a v-if="runningResearch" class="nav-link">
                            <svg-icon name="action/lifecycle/running" :original="true" height="20" class="rotating"/>
                        </a>
                    </li>
                    <li class="nav-item">
                        <a v-if="!runningResearch" v-tooltip.bottom="'Discover Now'" @click="startResearchNow" class="nav-link">
                            <svg-icon name="action/lifecycle/run" :original="true" height="20"/>
                        </a>
                        <a v-if="runningResearch" v-tooltip.bottom="'Stop Discovery'" @click="stopResearchNow" class="nav-link">
                            <svg-icon name="action/lifecycle/stop" :original="true" height="20"/>
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link">
                            <triggerable-dropdown size="lg" align="right" :arrow="false">
                                <div slot="trigger" @click="clearNotifications">
                                    <svg-icon name="navigation/notifications" :original="true" height="20"/>
                                    <span class="badge" v-if="notification.notificationUnseen.data"
                                    >{{ notification.notificationUnseen.data }}</span>
                                </div>
                                <div slot="content" class="preview-table">
                                    <h5>Notifications</h5>
                                    <div v-for="notification in notification.aggregatedNotificationList.data"
                                         @click="navigateNotification(notification.uuid)"
                                         class="notification" v-bind:class="{ 'bold': !notification.seen }">
                                        <div><status-icon :value="notification.severity"/></div>
                                        <div class="content">{{ notification.title }}</div>
                                        <div>{{ relativeDate(notification.date_fetched) }}</div>
                                    </div>
                                    <div v-if="!notification.aggregatedNotificationList.data.length" class="row empty">
                                        <i class="icon-checkmark2"></i>
                                    </div>
                                    <div class="view-all">
                                        <div @click="navigateNotifications" class="link">View History</div>
                                    </div>
                                </div>
                            </triggerable-dropdown>
                        </a>
                    </li>
                    <li class="nav-item">
                        <router-link :to="{ name: 'Settings' }" class="nav-link" tag="a">
                            <svg-icon name="navigation/settings" :original="true" height="20" />
                        </router-link>
                    </li>
                </ul>
            </div>
        </nav>
    </header>
</template>

<script>
    import { mixin as clickaway } from 'vue-clickaway'
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
	import StatusIcon from '../../components/StatusIcon.vue'
    import '../../components/icons'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_LIFECYCLE } from '../../store/modules/dashboard'
	import { TOGGLE_SIDEBAR } from '../../store/mutations'
    import {
        FETCH_NOTIFICATIONS_UNSEEN_COUNT,
        FETCH_NOTIFICATIONS,
        UPDATE_NOTIFICATIONS_SEEN,
        FETCH_NOTIFICATIONS_UNSEEN,
        FETCH_NOTIFICATION, notification
    } from '../../store/modules/notifications'
	import '../../components/icons/logo'
    import { START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '../../store/actions'

	export default {
		components: {TriggerableDropdown, StatusIcon},
		name: 'top-bar-container',
        mixins: [ clickaway ],
		computed: {
            ...mapState(['interaction', 'notification', 'dashboard']),
            lifecycle () {
                if (!this.dashboard.lifecycle.data.subPhases) return []

                return this.dashboard.lifecycle.data.subPhases
            }
        },
        data() {
			return {
				interval: null,
                isDown: false,
                runningResearch: false
			}
        },
		methods: {
			...mapMutations({toggleSidebar: TOGGLE_SIDEBAR}),
			...mapActions({
				fetchNotificationsUnseen: FETCH_NOTIFICATIONS_UNSEEN,
                fetchNotification: FETCH_NOTIFICATION,
				fetchNotifications: FETCH_NOTIFICATIONS,
                updateNotificationsSeen: UPDATE_NOTIFICATIONS_SEEN,
                fetchNotificationsUnseenCount: FETCH_NOTIFICATIONS_UNSEEN_COUNT,
                fetchLifecycle: FETCH_LIFECYCLE,
                startResearch: START_RESEARCH_PHASE,
                stopResearch: STOP_RESEARCH_PHASE,

			}),
			navigateNotification (notificationId) {
				this.fetchNotification(notificationId)
                this.$el.click()
				this.$router.push({path: `/notification/${notificationId}`})
			},
			relativeDate (timestamp) {
				let date = new Date(timestamp)
				let now = Date.now()
				if (now - date.getTime() < 24 * 60 * 60 * 1000) {
					return date.toLocaleTimeString()
				} else if (now - date.getTime() < 48 * 60 * 60 * 1000) {
					return 'Yesterday'
				}
				return date.toLocaleDateString()
			},
            loadNotifications() {
                this.fetchNotifications({aggregate: true})
                this.fetchNotificationsUnseenCount({})
            },
            clearNotifications() {
			    this.updateNotificationsSeen([])
            },
            navigateNotifications() {
                this.$el.click()
                this.$router.push({name: 'Notifications' })
            },
            startResearchNow() {
                this.runningResearch = true
                this.startResearch()
            },
            stopResearchNow() {
                this.runningResearch = false
                this.stopResearch()
            }
		},
		created () {
            this.loadNotifications()
            this.intervals = []
            this.intervals.push(setInterval(function () {
                this.loadNotifications()
            }.bind(this), 3000))
            this.fetchLifecycle()
            this.intervals.push(setInterval(function () {
                this.fetchLifecycle().then((response) => {
                    this.runningResearch = this.lifecycle.reduce((sum, item) => sum + item.status, 0) !== this.lifecycle.length
                })
            }.bind(this), 10000))
		},
		beforeDestroy () {
            this.intervals.forEach(interval => clearInterval(interval))
		}
	}
</script>

<style lang="scss">
    .topbar {
        background: $grey-1;
        position: relative;
        z-index: 101;
        .top-navbar {
            min-height: 50px;
            padding: 0;
            -ms-flex-direction: row;
            flex-direction: row;
            -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
            -ms-flex-pack: start;
            justify-content: flex-start;
            .navbar-logo {
                flex: 1 0 auto;
            }
            .navbar-header {
                background-color: $theme-black;
                line-height: 45px;
                text-align: center;
                width: 240px;
                flex-shrink: 0;
                transition: all ease-in 0.2s;
                .sidebartoggler {
                    text-align: left;
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
            .navbar-collapse {
                padding-left: 24px;
                padding-right: 12px;
                display: flex;
                display: -ms-flex;
            }
            i {
                font-size: 160%;
                vertical-align: middle;
            }
            i.ti-menu {
                font-size: 120%;
            }
            .navbar-nav {
                flex-direction: row;
                -ms-flex-direction: row;
            }
            .navbar-nav > .nav-item > .nav-link {
                padding-left: .75rem;
                padding-right: .75rem;
                line-height: 40px;
                color: $theme-black;
                .svg-stroke {
                    stroke: $theme-black;
                    stroke-width: 6px;
                }
                .svg-fill {
                    fill: $theme-black;
                }
                &:hover {
                    color: $theme-orange;
                    .show {
                        color: $theme-orange;
                    }
                    .svg-stroke {
                        stroke: $theme-orange;
                    }
                    .svg-fill {
                        fill: $theme-orange;
                    }
                }
            }
            .nav-item {
                margin-bottom: 0;
                .svg-icon{
                    margin: auto;
                }
            }
            .dropdown-menu {
                max-height: 30vh;
                overflow: auto;
            }
        }
        &.collapse {
            display: block;
            .navbar-header {
                width: 60px;
                text-align: center;
                span {
                    display: none;
                }
            }
        }
        .dropdown-toggle:after {
            display: none;
        }
        .svg-bg {
            stroke: $grey-1;
            fill: $grey-1;
        }
    }

    .fix-topbar {
        .topbar {
            position: fixed;
            width: 100%;
        }
    }

    .preview-table {
        color: $theme-black;
        line-height: initial;
        font-size: 12px;
        .empty {
            border-bottom: 1px solid $grey-2;
            border-top: 1px solid $grey-2;
            padding: 8px 0;
            i {
                margin: auto;
            }
        }
        .view-all {
            text-align: center;
            width: 100%;
            margin-bottom: -12px;
            line-height: 36px;
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

    .notification {
        display: grid;
        grid-template-columns: 20px auto 72px;
        grid-auto-flow: row;
        letter-spacing: 1px;
        grid-gap: 8px 4px;
        border-bottom: 1px solid $grey-2;
        padding: 8px 0;
        .content {
            text-overflow: ellipsis;
            overflow: hidden;
        }
        .status-icon {
            border-radius: 4px;
            .icon-info {
                padding: 0px;
            }
        }
    }

</style>