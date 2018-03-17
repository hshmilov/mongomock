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

	import { mapState, mapMutations, mapActions } from 'vuex'
	import { TOGGLE_SIDEBAR } from '../../store/mutations'
	import {
		FETCH_NOTIFICATIONS_UNSEEN,
		FETCH_NOTIFICATIONS_UNSEEN_COUNT,
		FETCH_NOTIFICATION
	} from '../../store/modules/notifications'
	import '../../components/icons/logo'

	export default {
		components: {TriggerableDropdown, StatusIcon},
		name: 'top-bar-container',
		computed: mapState(['interaction', 'notification']),
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
				fetchNotification: FETCH_NOTIFICATION
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
            }
		},
		mounted() {
            this.loadNotifications()
            this.interval = setInterval(function () {
                this.loadNotifications()
            }.bind(this), 60000);
		},
		beforeDestroy() {
			clearInterval(this.interval);
		}
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .topbar {
        background: $gray-light;
        position: relative;
        z-index: 50;
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
                background-color: $black;
                line-height: 45px;
                text-align: center;
                width: 240px;
                flex-shrink: 0;
                transition: all ease-in 0.2s;
                .sidebartoggler {
                    text-align: left;
                    color: $gray-dark;
                    &:hover {
                        color: $orange;
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
                color: $black;
                &:hover {
                    color: $orange;
                    .show {
                        color: $orange;
                    }
                }
            }
            .nav-item {
                margin-bottom: 0;
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
        color: $black;
        line-height: initial;
        font-size: 12px;
        .item {
            border-bottom: 1px solid $gray-dark;
            padding: 12px 12px;
            margin: 0 -12px;
            text-transform: none;
            letter-spacing: initial;
            &:first-of-type {
                border-top: 1px solid $gray-dark;
            }
            &:hover {
                color: $orange;
            }
            &.empty {
                color: $orange;
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

</style>