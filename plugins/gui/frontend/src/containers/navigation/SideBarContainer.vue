<template>
    <aside class="left-sidebar" v-bind:class="{ 'collapse': interaction.collapseSidebar || ($resize && $mq.below(1200)) }">
            <div class="scroll-sidebar">
                <div class="user">
                    <div class="user-profile">
                        <img :src="auth.data.pic_name" />
                        <h5>{{ `${auth.data.first_name} ${auth.data.last_name}` }}</h5>
                    </div>
                    <div class="user-actions">
                        <a @click="logout" class="" data-toggle="tooltip" title="Logout">
                            <i class="icon-logout"></i>
                        </a>
                    </div>
                </div>
                <nav class="sidebar-nav">
                    <nested-nav-bar>
                        <nested-nav-item routeName="Dashboard" routerPath="/" iconName="dashboard" :exact="true"></nested-nav-item>
                        <!--nested-nav-item routeName="Tasks" iconName="task" :disabled="true"></nested-nav-item-->
                        <nested-nav-item routeName="Devices" iconName="device">
                            <nested-nav-bar nestLevel="1" class="collapse">
                                <nested-nav-item routeName="Saved Queries"></nested-nav-item>
                                <nested-nav-item routeName="Queries History"></nested-nav-item>
                            </nested-nav-bar>
                        </nested-nav-item>
                        <nested-nav-item routeName="Users" iconName="user"></nested-nav-item>
                        <nested-nav-item routeName="Alerts" iconName="alert"></nested-nav-item>
                        <nested-nav-item routeName="Adapters" iconName="adapter"></nested-nav-item>
                    </nested-nav-bar>
                </nav>
            </div>
        <footer class="footer">
            <div class="content">© {{ (new Date()).getFullYear() }} Axonius</div></footer>
    </aside>
</template>

<script>
    import '../../components/icons/navigation'

    import NestedNavBar from '../../components/NestedNavBar.vue'
    import NestedNavItem from '../../components/NestedNavItem.vue'
    import { LOGOUT } from '../../store/modules/auth'
    import { mapState, mapActions } from 'vuex'

    export default {
        name: 'side-bar-container',
        components: { NestedNavBar, NestedNavItem },
        computed: mapState([ 'auth', 'interaction' ]),
        methods: mapActions({ logout: LOGOUT })
    }
</script>

<style lang="scss">
    @import '../../scss/config';

    .left-sidebar {
        position: absolute;
        width: 240px;
        transition: all ease-in 0.2s;
        height: 100%;
        z-index: 20;
        padding-top: 60px;
        background: $color-theme-dark;
        .scroll-sidebar {
            padding-bottom: 60px;
            display: flex;
            flex-flow: column;
            height: 100%;
            transition: all ease-in 0.2s;
            .user {
                flex: 0 1 auto;
                position: relative;
                font-size: $font-size-title;
                width: 100%;
                overflow-x: hidden;
                transition: all ease-in 0.2s;
                .user-profile {
                    text-align: center;
                    margin: 0 auto;
                    padding: 10px 0 5px 0;
                    border-radius: 100%;
                    width: 240px;
                    img {
                        width: 50px;
                        padding: 4px;
                        border-radius: 100%;
                    }
                    h5 {
                        color: $color-btn;
                        display: inline-block;
                    }
                }
                .user-actions {
                    padding: 4px 0px;
                    position: relative;
                    text-align: center;
                    > a {
                        color: $color-btn;
                        padding: 0 4px;
                        &:hover {  color: $color-btn-hover;  }
                        &:after {  display: none;  }
                    }
                }
            }
            .sidebar-nav {
                overflow: hidden;
                background: $color-theme-dark;
                padding: 0px;
                padding-top: 30px;
                .nav-nest {
                    transition: all ease-in 0.2s;
                }
                .nav-link.has-arrow::after {
                    transition: all ease-in 0.2s;
                    opacity: 1;
                }
            }
        }
        .footer {
            position: absolute;
            width: 100%;
            bottom: 0;
            color: $color-btn;
            padding: 12px 4px;
            border-top: 1px solid $color-btn;
            background: $color-theme-dark;
            transition: all ease-in 0.2s;
            overflow-x: hidden;
            .content {
                width: 240px;
                overflow-x: visible;
            }
        }
    }

    .fix-sidebar .left-sidebar {  position: fixed;  }

    .left-sidebar.collapse {
        display: block;
        width: 60px;
        .scroll-sidebar {
            padding-bottom: 0px;
            position: absolute;
            width: 60px;
            .user {
                .user-profile {
                    text-align: left;
                    margin-left: 4px;
                }
            }
            .sidebar-nav {
                overflow: visible;
                .nav-nest .nav-link span {
                    opacity: 0;
                }
                .nav-item {
                    overflow: hidden;
                    .nav-nest.collapse {
                        display: none;
                        transition: all ease-in 0.2s;
                    }
                    &:hover {
                        overflow: visible;
                        position: relative;
                        .nav-nest.collapse {
                            left: 56px;
                            margin-left: 0;
                            top: 0;
                            position: absolute;
                            background-color: $color-theme-dark;
                            display: block;
                            .nav-link span {
                                transition: all ease-in 0.5s;
                                opacity: 1;
                            }
                        }
                    }
                }
                .nav-link.has-arrow::after {
                    opacity: 0;
                }
            }
        }
        .scrollbar-container, .sidebar-nav {  background: transparent;  }
    }


</style>