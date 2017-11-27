<template>
    <aside class="left-sidebar" v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
            <div class="scroll-sidebar">
                <div class="user-profile">
                    <div class="user-profile-img">
                        <img :src="user.picname" />
                    </div>
                    <div class="user-profile-text">
                        <h5 class="collapse-hidden">{{ `${user.firstname} ${user.lastname}` }}</h5>
                        <a href="#" class="" data-toggle="tooltip" title="Logout">
                            <i class="icon-logout"></i>
                        </a>
                    </div>
                </div>
                <vue-scrollbar class="scrollbar-container" ref="Scrollbar">
                    <nav class="sidebar-nav">
                        <nested-nav-bar>
                            <nested-nav-item routeName="Dashboard" routerPath="/" iconName="dashboard" :exact="true"></nested-nav-item>
                            <nested-nav-item routeName="Devices" iconName="device">
                                <nested-nav-bar nestLevel="1" class="collapse">
                                    <nested-nav-item routeName="Saved Queries"></nested-nav-item>
                                    <nested-nav-item routeName="Queries History"></nested-nav-item>
                                </nested-nav-bar>
                            </nested-nav-item>
                            <nested-nav-item routeName="Plugins" iconName="plugin"></nested-nav-item>
                            <nested-nav-item routeName="Adapters" iconName="adapter"></nested-nav-item>
                            <nested-nav-item routeName="Tasks" iconName="task"></nested-nav-item>
                            <nested-nav-item routeName="Alerts" iconName="alert"></nested-nav-item>
                        </nested-nav-bar>
                    </nav>
                </vue-scrollbar>
            </div>
            <footer class="footer">© {{ (new Date()).getFullYear() }} Axonius</footer>
    </aside>
</template>

<script>
    import '../../components/icons/navigation'

    import VueScrollbar from 'vue2-scrollbar'
    import NestedNavBar from '../../components/NestedNavBar.vue'
    import NestedNavItem from '../../components/NestedNavItem.vue'
    import { mapState } from 'vuex'

    export default {
        name: 'side-bar-container',
        components: { VueScrollbar, NestedNavBar, NestedNavItem },
        computed: mapState([ 'user', 'interaction' ])
    }
</script>

<style lang="scss">
    @import '../../scss/config';

    .left-sidebar {
        position: absolute;
        width: 240px;
        height: 100%;
        top: 0px;
        z-index: 20;
        padding-top: 60px;
        background: $color-theme-dark;
        .footer {
            position: absolute;
            width: 100%;
            bottom: 0;
            color: $color-light;
            padding: 17px 15px;
            border-top: 1px solid $color-light;
            background: $color-theme-dark;
        }
    }

    .fix-sidebar .left-sidebar {  position: fixed;  }

    .user-profile {
        position: relative;
        background-size: cover;
        font-size: $font-size-title;
        .user-profile-img {
            width: 70px;
            margin: 0 auto;
            padding: 10px 0 5px 0;
            border-radius: 100%;
            img {
                width: 100%;
                padding: 5px;
                border-radius: 100%;
            }
        }
        .user-profile-text {
            padding: 5px 0px;
            position: relative;
            text-align: center;
            h5 {
                color: $color-light;
            }
            > a {
                color: $color-light;
                padding: 0 5px;
                &:hover {  color: $color-theme-light;  }
                &:after {  display: none;  }
            }
        }
    }

    .scroll-sidebar {
        padding-bottom: 60px;
        display: flex;
        flex-flow: column;
        height: 100%;
        .user-profile {  flex: 0 1 auto;  }
        .scrollbar-container {
            background-color: $color-theme-dark;
            flex: 1 1 auto;
            margin: 0;
        }
    }

    .sidebar-nav {
        background: $color-theme-dark;
        padding: 0px;
        padding-top: 30px;
    }

    .left-sidebar.collapse {
        display: block;
        width: 60px;
        .collapse-hidden, .has-arrow:after {
            display: none;
        }
        .user-profile {
            padding-bottom: 15px;
            width: 60px;
            margin-bottom: 7px;
            .user-profile-img {
                width: 50px;
                padding: 15px 0 0 0;
                margin: 0px 0 0 6px;
                &:before {  top: 15px;  }
            }
            .user-profile-text a {
                display: block;
                margin-top: 15px;
            }
        }
        .scroll-sidebar {
            padding-bottom: 0px;
            position: absolute;
            overflow-x: hidden !important;
        }
        .scrollbar-container, .sidebar-nav {  background: transparent;  }
        .nav-item.active .nav-nest.collapse {
            display: none;
        }
        .expand-nav .nav-item {
            width: 60px;
            .nav-nest {
                position: absolute;
                left: 20px;
                top: 70px;
                width: 0;
                z-index: 1001;
                background: $color-theme-light;
                opacity: 0.5;
                display: none;
                padding-left: 1px;
            }
            .nav-link {
                width: 120px;
                font-size: 80%;
            }
            &:hover {
                width: 180px;
                .nav-nest {
                    height: auto !important;
                    overflow: auto;
                    display: block;
                    width: 120px;
                    overflow-x: hidden;
                    &.collapse {  display: block;  }
                }
                .nav-link {
                    width: 180px;
                    color: $color-light;
                    background: $color-theme-light;
                    opacity: 0.5;
                    .collapse-hidden {  display: inline;  }
                    span {  opacity: 1;  }
                }
                .svg-icon {
                    .svg-fill {  fill: $color-light  }
                    .svg-stroke {  stroke: $color-light  }
                }
            }
            &.active {
                .nav-nest.collapse {  display: none;  }
                &:hover .nav-nest.collapse {  display: block;  }
            }
        }
        footer {
            display: none;
        }
    }


</style>