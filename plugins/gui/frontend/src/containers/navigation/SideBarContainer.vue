<template>
    <aside class="x-side-bar" v-bind:class="{ collapse: collapseSidebar }">
        <div class="x-user">
            <div class="x-user-profile">
                <img :src="userDetails.pic" />
                <h5>{{ userDetails.name }}</h5>
            </div>
            <div class="x-user-actions">
                <a @click="logout" title="Logout">
                    <svg-icon name="navigation/logout" height="16" :original="true" />
                </a>
                <router-link :to="{name: 'My Account'}" active-class="active" @click.native="$emit('click')" title="My Account">
                    <svg-icon name="navigation/settings" height="16" :original="true" />
                </router-link>
            </div>
        </div>
        <x-nested-nav>
            <x-nested-nav-item v-bind="navigationLinkProps('Dashboard')" icon="dashboard" :exact="true" id="dashboard" />
            <x-nested-nav-item v-bind="navigationLinkProps('Devices')" icon="devices" id="devices" />
            <x-nested-nav-item v-bind="navigationLinkProps('Users')" icon="users" id="users" />
            <x-nested-nav-item v-bind="navigationLinkProps('Alerts')" icon="alert" id="alerts" />
            <x-nested-nav-item v-bind="navigationLinkProps('Adapters')" icon="adapter" id="adapters" />
            <x-nested-nav-item v-bind="navigationLinkProps('Reports')" icon="report" id="reports" />
            <x-nested-nav-item v-bind="navigationLinkProps('Instances')" icon="instances" id="instances" />
        </x-nested-nav>
    </aside>
</template>

<script>
    import xNestedNav from '../../components/menus/NestedNav.vue'
    import xNestedNavItem from '../../components/menus/NestedNavItem.vue'

    import { LOGOUT } from '../../store/modules/auth'
    import { mapState, mapActions } from 'vuex'

    export default {
        name: 'side-bar-container',
        components: { xNestedNav, xNestedNavItem },
        computed: mapState({
            userDetails(state) {
                return {
                    name: `${state.auth.currentUser.data.first_name} ${state.auth.currentUser.data.last_name}`,
                    pic: state.auth.currentUser.data.pic_name
                }
            },
            userPermissions(state) {
                return state.auth.currentUser.data.permissions
            },
            collapseSidebar(state) {
                return state.interaction.collapseSidebar || state.interaction.windowWidth <= 1200
            }
        }),
        methods: {
            ...mapActions({ logout: LOGOUT }),
            navigationLinkProps(name) {
                let restricted = this.isRestricted(name)
                return {
                    name,
                    disabled: restricted,
                    clickHandler: restricted? this.notifyAccess : undefined
                }
            },
            isRestricted(name) {
                return this.userPermissions && this.userPermissions[name] === 'Restricted'
            },
            notifyAccess(name) {
                this.$emit('access-violation', name)
            }
        }
    }
</script>

<style lang="scss">
    .x-side-bar {
        position: fixed;
        top: 0;
        width: 240px;
        transition: all ease-in 0.2s;
        height: 100%;
        z-index: 100;
        background: $theme-black;
        padding: 60px 0;
        display: flex;
        flex-flow: column;
        .x-user {
            flex: 0 1 auto;
            position: relative;
            font-size: 16px;
            width: 100%;
            overflow-x: hidden;
            transition: all ease-in 0.2s;
            margin-bottom: 48px;
            .x-user-profile {
                text-align: center;
                margin: 0 auto;
                padding: 10px 0 5px 0;
                border-radius: 100%;
                width: 240px;
                img {
                    width: 60px;
                    margin-bottom: 8px;
                    border-radius: 100%;
                }
                h5 {
                    color: $theme-white;
                    margin-bottom: 0;
                    transition: all ease-in 0.2s;
                }
            }
            .x-user-actions {
                padding: 4px 0px;
                position: relative;
                text-align: center;
                > a {
                    color: $grey-4;
                    padding: 0 4px;
                    .svg-fill {  fill: $grey-4;  }
                    .svg-stroke {  stroke: $grey-4;  }
                    &:hover, &.active {
                        color: $theme-white;
                        .svg-fill {  fill: $theme-white;  }
                        .svg-stroke {  stroke: $theme-white;  }
                    }
                    &:after {  display: none;  }
                }
            }
        }
        > .x-nested-nav > .x-nested-nav-item {
            border-left: 2px solid transparent;
            > .item-link {
                width: 58px;
            }
            &.active {
                border-left: 2px solid $theme-orange;
            }
            .x-nested-nav {
                display: none;

            }
            &.active > .x-nested-nav {
                display: block;
            }
        }
    }
    .x-side-bar.collapse {
        display: block;
        width: 60px;
        padding-bottom: 0;
        .x-user {
            .x-user-profile {
                text-align: left;
                h5 {
                    opacity: 0;
                }
            }
        }
    }


</style>