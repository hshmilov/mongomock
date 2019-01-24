<template>
    <div class="x-nested-nav" :class="{active: subIsActive()}">
        <button class="item-link" :title="name" @click='toggleSubMenu'>
            <svg-icon  v-if="icon" :name="`navigation/${icon}`" width="24" :original="true" />
            <span>{{ name }}</span>
        </button>
        <slot v-if="!collapseSidebar && isOpen"/>
    </div>
</template>

<script>
    import {TOGGLE_SIDEBAR} from '../../../store/mutations'
    import {mapMutations, mapState} from 'vuex'
    export default {
        name: 'x-nested-nav',
        props: ['name', 'icon', 'childRoot'],
        computed: mapState({
            collapseSidebar(state) {
                return state.interaction.collapseSidebar
            }
        }),
        methods: {
            ...mapMutations({
                toggleSidebar: TOGGLE_SIDEBAR
            }),
            toggleSubMenu() {
                if (this.collapseSidebar) {
                    this.toggleSidebar()
                    this.isOpen = true
                }
                else {
                    this.isOpen = !this.isOpen
                }
            },
            subIsActive() {
                const paths = Array.isArray(this.childRoot) ? this.childRoot : [this.childRoot];
                return paths.some(path => {
                    return this.$route.path.indexOf(path) === 0
                })
            }
        },
        data() {
            return {
                isOpen: false
            }
        },
    }
</script>

<style lang="scss">
    .x-nested-nav {
        transition: all ease-in 0.2s;
        text-transform: capitalize;
        list-style: none;
        position: relative;
        .item-link {
            transition: all ease-in 0.2s;
            color: $grey-4;
            font-weight: 200;
            padding: 8px 16px;
            display: block;
            white-space: nowrap;
            letter-spacing: 2px;
            font-size: 14px;
            background-color: $theme-black;
            border: 0;
            cursor: pointer;
            .svg-icon {
                transition: all ease-in 0.2s;
                margin-right: 10px;
                .svg-fill {  fill: $grey-4  }
                .svg-stroke {  stroke: $grey-4  }
                stroke-width: 24px;
            }
        }
        &.disabled {
            .svg-icon {
                .svg-fill {  fill: $grey-5;  }
                .svg-stroke {  stroke: $grey-5;  }
            }
            .item-link {
                cursor: default;
            }
        }
        &:not(.disabled):hover, &.active {
            >.item-link {
                color: $theme-orange;
            }
            .svg-icon {
                .svg-fill {  fill: $theme-orange;  }
                .svg-stroke {  stroke: $theme-orange;  }
            }
        }
        &.active {
            .x-nav {
                padding-left: 36px;
                background-color: $grey-5;
                overflow: hidden;
                .x-nested-nav {
                    .item-link {
                        color: $theme-white;
                        background-color: $grey-5;
                        &:hover {
                            color: $theme-orange;
                        }
                    }
                    &.active .item-link {
                        color: $theme-orange;
                    }
                }
                &.collapse {
                    display: block;
                }
            }
        }
    }

</style>