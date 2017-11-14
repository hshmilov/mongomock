<template>
    <header class="topbar" v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
        <nav class="navbar top-navbar navbar-expand-md navbar-light">
            <div class="navbar-header">
                <a class="navbar-brand">
                    <b><svg-icon name="logo/logo" height="36"></svg-icon></b>
                    <span><svg-icon name="logo/axonius" height="20"></svg-icon></span>
                </a>
            </div>
            <div class="navbar-collapse">
                <ul class="navbar-nav mr-auto mt-md-0">
                    <li class="nav-item m-l-10">
                        <a class="nav-link sidebartoggler hidden-sm-down" v-on:click="toggleSidebar">
                            <i class="icon-menu"></i>
                        </a>
                    </li>
                    <li class="nav-item">
                        <router-link :to="{ name: 'Dashboard' }" class="nav-link nav-home" exact-active-class="active">
                            <i class="icon-home"></i>
                        </router-link>
                    </li>
                </ul>
                <ul class="navbar-nav my-lg-0">
                    <li class="nav-item">
                        <a class="nav-link">
                            <i class="icon-bell-o"></i>
                        </a>
                    </li>
                    <li class="nav-item">
                        <router-link :to="{ name: 'Settings' }" class="nav-link">
                            <i class="icon-cog"></i>
                        </router-link>
                    </li>
                </ul>
            </div>
        </nav>
    </header>
</template>

<script>
    import { mapState, mapMutations } from 'vuex'
    import { TOGGLE_SIDEBAR } from '../../store/mutations'
    import '../../components/icons/logo'

    export default {
        name: 'top-bar-container',
        computed: mapState([ 'interaction' ]),
        methods: mapMutations({ toggleSidebar: TOGGLE_SIDEBAR })
    }
</script>

<style lang="scss">
    @import '../../assets/scss/config';

    .topbar {
        background: $color-theme;
        position: relative;
        z-index: 50;
        .top-navbar {
            min-height: 50px;
            padding: 0px 15px 0 0;
            -ms-flex-direction: row;
            flex-direction: row;
            -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
            -ms-flex-pack: start;
            justify-content: flex-start;
            .navbar-header {
                background-color: $background-color-light;
                line-height: 45px;
                text-align: center;
                width: 240px;
                flex-shrink: 0;
                .navbar-brand {
                    margin-right: 0px;
                    padding-bottom: 0px;
                    padding-top: 0px;
                    b {
                        line-height: 62px;
                        display: inline-block;
                    }
                    .svg-icon {  fill: $color-theme;  }
                }
            }
            .navbar-collapse {
                display: flex;
                display: -ms-flex;
            }
            i {
                font-size: 200%;
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
                color: $color-light;
            }
            .nav-item {  margin-bottom: 0;  }
            .nav-link.nav-home.active, .nav-link.nav-home:hover {  color: $color-yellow;  }
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
    }

    .fix-topbar {
        .topbar {
            position: fixed;
            width: 100%;
        }
    }

    @media #{$media-break-md} {
        
    }

</style>