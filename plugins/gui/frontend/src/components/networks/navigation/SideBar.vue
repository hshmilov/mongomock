<template>
    <aside class="x-side-bar" :class="{ collapse: collapseSidebar }">
        <div class="x-user">
            <div v-if="medicalConfig" class="x-user-profile medical">
                <svg-icon :name=logoSVG :height=logoSize :original="true"/>
            </div>
            <div v-else class="x-user-profile">
                <img :src="userDetails.pic"/>
                <h5>{{ userDetails.name }}</h5>
            </div>
            <div  v-if="!medicalConfig" class="x-user-actions">
                <a @click="onLogout" title="Logout">
                    <svg-icon name="navigation/logout" height="16" :original="true"/>
                </a>
                <router-link :to="{name: 'My Account'}" active-class="active" @click.native="$emit('click')"
                             title="My Account">
                    <svg-icon name="navigation/settings" height="16" :original="true"/>
                </router-link>
            </div>
        </div>
        <x-nav v-if="medicalConfig">
            <x-nav-item v-bind="navigationProps('Fleet Viewer')" icon="reports" :exact="true" id="fleet"/>
            <x-nav-item v-bind="navigationProps('Infuser Programing')" icon="pairing" id="pairing"/>
            <x-nested-nav name="Infuser Manager" icon="settings" childRoot="/infuser_manager">
                <x-nav-item v-bind="navigationProps('Infuser Settings')" id="infuser_settings"/>
                <x-nav-item v-bind="navigationProps('Treatments Settings')" id="treatments_settings"/>
                <x-nav-item v-bind="navigationProps('Drug List Settings')" id="drug_list_settings"/>
                <x-nav-item v-bind="navigationProps('Preset Programs')" id="preset_programs"/>
            </x-nested-nav>
        </x-nav>
        <x-nav v-else>
            <x-nav-item v-bind="navigationProps('Dashboard', 'dashboard')" :exact="true" />
            <x-nav-item v-bind="navigationProps('Devices', 'devices')" />
            <x-nav-item v-bind="navigationProps('Users', 'users')" />
            <x-nav-item v-bind="navigationProps('Enforcements', 'enforcements', 'Enforcement Center')" />
            <x-nav-item v-bind="navigationProps('Adapters', 'adapters')" />
            <x-nav-item v-bind="navigationProps('Reports', 'reports')" />
            <x-nav-item v-bind="navigationProps('Instances', 'instances')" />
        </x-nav>
    </aside>
</template>

<script>
    import xNav from '../../axons/menus/Nav.vue'
    import xNavItem from '../../axons/menus/NavItem.vue'
    import xNestedNav from '../../axons/menus/NestedNav.vue'

    import {mapState} from 'vuex'

    export default {
        name: 'x-side-bar',
        components: {xNav, xNavItem, xNestedNav},
        computed: {...mapState({
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
                return state.interaction.collapseSidebar
            },
            medicalConfig(state) {
                return state.staticConfiguration.medicalConfig
            },
        }),
        logoSize: {
            get(){
                return this.collapseSidebar ? '47' : '114'
            }
        },
        logoSVG: {
            get(){
                return this.collapseSidebar ? 'logo/avoset-mini' : 'logo/avoset'
            }
        }
        },
        methods: {
            navigationProps(name, id, title) {
                let restricted = this.isRestricted(name)
                return {
                    id,
                    name,
                    title,
                    icon: id,
                    disabled: restricted,
                    clickHandler: restricted ? this.notifyAccess : undefined
                }
            },
            isRestricted(name) {
                return this.userPermissions && this.userPermissions[name] === 'Restricted'
            },
            notifyAccess(name) {
                this.$emit('access-violation', name)
            },
            onLogout() {
                try {
                    const auth2 = window.gapi.auth2.getAuthInstance()
                    auth2.signOut()
                } catch (err) {
                }
                window.location.replace(window.location.origin + '/api/logout')
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

                    .svg-fill {
                        fill: $grey-4;
                    }

                    .svg-stroke {
                        stroke: $grey-4;
                    }

                    &:hover, &.active {
                        color: $theme-white;

                        .svg-fill {
                            fill: $theme-white;
                        }

                        .svg-stroke {
                            stroke: $theme-white;
                        }
                    }

                    &:after {
                        display: none;
                    }
                }
            }
        }

        > .x-nav {
            width: 100%;
            > .x-nav-item {
                border-left: 2px solid transparent;

                > .item-link {
                    width: 100%;
                    height: 100%;
                    text-align: left;
                }

                &.active {
                    border-left: 2px solid $theme-orange;
                }

                .x-nav {
                    display: none;

                }

                &.active > .x-nav {
                    display: block;
                }
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
            .medical {
                padding-top: 18px;
            }
        }
    }
    .x-side-bar.collapse .x-nav {
        overflow: visible;
        .x-nested-nav {
            overflow: hidden;
            .item-link span {
                transition: all ease-in 0.2s;
                opacity: 0;
                line-height: 20px;
            }
            .x-nav.collapse {
                display: none;
            }
            &:hover {
                overflow: hidden;
                position: relative;
                .x-nav.collapse {
                    left: 58px;
                    margin-left: 0;
                    top: 0;
                    position: absolute;
                    background-color: $grey-5;
                    padding-left: 0;
                    display: block;
                    .item-link span {
                        opacity: 1;
                    }
                }
            }
        }
    }
</style>