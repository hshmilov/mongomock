<template>
    <header class="topbar" v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <nav class="navbar top-navbar navbar-expand-md navbar-light">
            <div class="navbar-header">
                <li class="nav-item m-l-10">
                    <a class="nav-link sidebartoggler hidden-sm-down" v-on:click="toggleSidebar">
                        <i class="icon-menu"></i>
                    </a>
                </li>
            </div>
            <div class="navbar-collapse">
                <ul class="navbar-nav mr-auto mt-md-0">
                    <a class="navbar-brand">
                        <b><svg-icon name="logo/logo" height="30" :original="true"></svg-icon></b>
                        <span><svg-icon name="logo/axonius" height="16" :original="true"></svg-icon></span>
                    </a>
                </ul>
                <ul class="navbar-nav my-lg-0">
                    <li class="nav-item">
                        <a class="nav-link">
                            <dropdown-menu animateClass="scale-up right" menuClass="w-lg">
                                <i slot="dropdownTrigger" class="icon-bell-o"></i>
                                <div slot="dropdownContent" class="preview-table" v-if="notification.notificationList.data">
                                    <h5>Notifications</h5>
                                    <div v-for="notification in notification.notificationList.data.slice(0, 5)"
                                         @click="navigateNotification(notification.uuid)" class="item row"
                                         v-bind:class="{ 'bold': !notification.seen }">
                                        <status-icon :value="notification.severity"></status-icon>
                                        <div class="col-10">{{ notification.title }}</div>
                                        <div>{{ relativeDate(notification.date_fetched) }}</div>
                                    </div>
                                    <div class="view-all">
                                        <router-link :to="{name: 'Notifications' }">View History</router-link>
                                    </div>
                                </div>
                            </dropdown-menu>
                        </a>
                    </li>
                    <li class="nav-item">
                        <!--<router-link :to="{ name: 'Settings' }" class="nav-link">-->
                        <a class="nav-link">
                            <i class="icon-cog"></i>
                        </a>
                        <!--</router-link>-->
                    </li>
                </ul>
            </div>
        </nav>
    </header>
</template>

<script>
	import DropdownMenu from '../../components/DropdownMenu.vue'
    import StatusIcon from '../../components/StatusIcon.vue'

	import { mapState, mapMutations, mapActions } from 'vuex'
	import { TOGGLE_SIDEBAR } from '../../store/mutations'
    import { FETCH_NOTIFICATIONS, FETCH_NOTIFICATION } from '../../store/modules/notifications'
    import { parseTime, parseDate } from '../../utils'
	import '../../components/icons/logo'

    export default {
		components: { DropdownMenu, StatusIcon },
		name: 'top-bar-container',
        computed: mapState([ 'interaction', 'notification' ]),
        methods: {
            ...mapMutations({ toggleSidebar: TOGGLE_SIDEBAR }),
            ...mapActions({ fetchNotifications: FETCH_NOTIFICATIONS, fetchNotification: FETCH_NOTIFICATION }),
            navigateNotification(notificationId) {
				this.fetchNotification(notificationId)
				this.$router.replace({path: `/notification/${notificationId}`})
            },
            relativeDate(originalDate) {
            	let timestamp = new Date(originalDate).getTime()
                let now = Date.now()
                if (now - timestamp < 24 * 60 * 60 * 1000) {
                	return parseTime(timestamp)
                } else if (now - timestamp < 48 * 60 * 60 * 1000) {
                	return "Yesterday"
                }
                return parseDate(timestamp)
            }
		},
        mounted() {
            this.fetchNotifications({
                skip: 0, limit: 50
            })
        }
    }
</script>

<style lang="scss">
    @import '../../scss/config';

    .topbar {
        background: $color-light;
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
            .navbar-brand {
                margin-right: 0px;
                padding-bottom: 0px;
                padding-top: 0px;
                cursor: default;
                b {
                    line-height: 62px;
                    display: inline-block;
                }
            }
            .navbar-header {
                background-color: $color-theme-dark;
                line-height: 45px;
                text-align: center;
                width: 240px;
                flex-shrink: 0;
                .sidebartoggler {
                    color: $color-theme-light;
                    text-align: right;
                    padding-right: 12px;
                }
            }
            .navbar-collapse {
                -webkit-box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.1);
                box-shadow: 0 1px 4px 0 rgba(0, 0, 0, 0.1);
                padding-left: 24px;
                padding-right: 12px;
                display: flex;
                display: -ms-flex;
            }
            i {
                font-size: 160%;
                vertical-align: middle;
            }
            i.ti-menu {  font-size: 120%;  }
            .navbar-nav {
                flex-direction: row;
                -ms-flex-direction: row;
            }
            .navbar-nav>.nav-item>.nav-link {
                padding-left: .75rem;
                padding-right: .75rem;
                line-height: 40px;
                color: $color-theme-dark;
                &:hover {
                    color: $color-theme-light;
                }
            }
            .nav-item {  margin-bottom: 0;  }
            .nav-link.nav-home.active, .nav-link.nav-home:hover {  color: $color-warning;  }
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
        color: $color-text-main;
        line-height: initial;
        font-size: 12px;
        .item {
            border-bottom: 1px solid $border-color;
            padding: 12px 12px;
            margin: 0 -12px;
            text-transform: none;
            letter-spacing: initial;
            &:first-of-type {
                border-top: 1px solid $border-color;
            }
            &:hover {
                color: $color-theme-light
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