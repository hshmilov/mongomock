<template>
    <header class="topbar" v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <nav class="navbar top-navbar navbar-expand navbar-light">
            <div class="navbar-header">
                <a class="nav-link sidebartoggler hidden-sm-down" v-on:click="toggleSidebar">
                    <i class="icon-menu"></i>
                </a>
            </div>
            <div class="navbar-collapse">
                <div class="navbar-logo">
                    <svg-icon name="logo/logo" height="30" :original="true"></svg-icon>
                    <svg-icon name="logo/axonius" height="16" :original="true"></svg-icon>
                </div>
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a v-if="!isRunning" v-tooltip.bottom="'Discover Now'" @click="startResearch" class="nav-link">
                            <svg-icon name="action/lifecycle/run" :original="true" height="20"></svg-icon>
                        </a>
                        <a v-if="isRunning" class="nav-link">
                            <svg-icon name="action/lifecycle/running" :original="true" height="20" class="rotating"></svg-icon>
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link">
                            <triggerable-dropdown size="lg" align="right" :arrow="false">
                                <div slot="dropdownTrigger">
                                    <i class="icon-bell-o"></i>
                                    <span class="badge" v-if="notification.notificationUnseen.data.count"
                                    >{{ notification.notificationUnseen.data.count }}</span>
                                </div>
                                <div slot="dropdownContent" class="preview-table">
                                    <h5>Notifications</h5>
                                    <div v-for="notification in notification.notificationUnseen.data.list"
                                         @click="navigateNotification(notification.uuid)" class="item row"
                                         v-bind:class="{ 'bold': !notification.seen }">
                                        <status-icon :value="notification.severity"/>
                                        <div class="col">{{ notification.title }}</div>
                                        <div>{{ relativeDate(notification.date_fetched) }}</div>
                                    </div>
                                    <div v-if="!notification.notificationUnseen.data.list.length" class="item row empty">
                                        <i class="icon-checkmark2"></i>
                                    </div>
                                    <div class="view-all">
                                        <router-link :to="{name: 'Notifications' }">View History</router-link>
                                    </div>
                                </div>
                            </triggerable-dropdown>
                        </a>
                    </li>
                    <li class="nav-item">
                        <router-link :to="{ name: 'Settings' }" class="nav-link" tag="a">
                            <i class="icon-settings"></i>
                        </router-link>
                    </li>
                </ul>
            </div>
        </nav>
    </header>
</template>

<script>
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
	import StatusIcon from '../../components/StatusIcon.vue'
    import '../../components/icons'

	import { mapState, mapMutations, mapActions } from 'vuex'
    import { FETCH_LIFECYCLE } from '../../store/modules/dashboard'
	import { TOGGLE_SIDEBAR } from '../../store/mutations'
	import {
		FETCH_NOTIFICATIONS_UNSEEN,
		FETCH_NOTIFICATIONS_UNSEEN_COUNT,
		FETCH_NOTIFICATION
	} from '../../store/modules/notifications'
	import '../../components/icons/logo'
    import { START_RESEARCH_PHASE } from '../../store/actions'

	export default {
		components: {TriggerableDropdown, StatusIcon},
		name: 'top-bar-container',
		computed: {
            ...mapState(['interaction', 'notification', 'dashboard']),
            lifecycle () {
                if (!this.dashboard.lifecycle.data.subPhases) return []

                return this.dashboard.lifecycle.data.subPhases
            },
            isRunning () {
                return this.lifecycle.reduce((sum, item) => sum + item.status, 0) !== this.lifecycle.length
            }
        },
        data() {
			return {
				interval: null
			}
        },
		methods: {
			...mapMutations({toggleSidebar: TOGGLE_SIDEBAR}),
			...mapActions({
				fetchNotificationsUnseen: FETCH_NOTIFICATIONS_UNSEEN,
				fetchNotificationsUnseenCount: FETCH_NOTIFICATIONS_UNSEEN_COUNT,
				fetchNotification: FETCH_NOTIFICATION,
                fetchLifecycle: FETCH_LIFECYCLE,
                startResearch: START_RESEARCH_PHASE,

			}),
			navigateNotification (notificationId) {
				this.fetchNotification(notificationId)
				this.$router.replace({path: `/notification/${notificationId}`})
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
                this.fetchNotificationsUnseenCount({})
                this.fetchNotificationsUnseen({
                    skip: 0, limit: 5
                })
            },

		},
		created () {
            this.loadNotifications()
            this.intervals = []
            this.intervals.push(setInterval(function () {
                this.loadNotifications()
            }.bind(this), 60000))
            this.fetchLifecycle()
            this.intervals.push(setInterval(function () {
                this.fetchLifecycle()
            }.bind(this), 500))
		},
		beforeDestroy () {
            this.intervals.forEach(interval => clearInterval(interval))
		}
	}
</script>

<style lang="scss">
    .topbar {
        background: $theme-gray-light;
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
                    color: $theme-gray-dark;
                    &:hover {
                        color: $theme-orange;
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
        .item {
            border-bottom: 1px solid $theme-gray-dark;
            padding: 12px 12px;
            margin: 0 -12px;
            text-transform: none;
            letter-spacing: initial;
            &:first-of-type {
                border-top: 1px solid $theme-gray-dark;
            }
            &:hover {
                color: $theme-orange;
            }
            &.empty {
                color: $theme-orange;
                cursor: default;
                i {
                    margin: auto;
                }
            }
            .status-icon {
                text-align: center;
                width: 20px;
                i {
                    font-size: 120%;
                    padding: 0;
                }
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

</style>