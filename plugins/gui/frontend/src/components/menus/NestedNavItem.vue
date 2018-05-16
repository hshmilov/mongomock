<template>
    <router-link tag="li" :to="disabled? {}: link" class="x-nested-nav-item"
                 :active-class="(!disabled && !exact)? 'active': ''"
                 :exact-active-class="(!disabled && exact)? 'active': ''">
        <a class="item-link" :title="routeName">
            <svg-icon v-if="iconName" :name="`navigation/${iconName}`" height="24" width="24" :original="true" />
            <span>{{ routeName }}</span>
        </a>
        <slot/>
    </router-link>
</template>

<script>
    export default {
		name: 'x-nested-nav-item',
		props: ['routeName', 'routerPath', 'iconName', 'exact', 'disabled'],
        computed: {
            link() {
            	if (this.routerPath) return { path: this.routerPath }
            	return { name: this.routeName }
            }
        }
    }
</script>

<style lang="scss">
    .x-nested-nav-item {
        transition: all ease-in 0.2s;
        text-transform: capitalize;
        list-style: none;
        .item-link {
            transition: all ease-in 0.2s;
            color: $grey-4;
            font-weight: 200;
            padding: 8px 16px;
            display: block;
            white-space: nowrap;
            letter-spacing: 2px;
            .svg-icon {
                transition: all ease-in 0.2s;
                margin-right: 10px;
                .svg-fill {  fill: $grey-4  }
                .svg-stroke {  stroke: $grey-4  }
                stroke-width: 24px;
            }
        }
        &:hover, &.active {
            >.item-link {  color: $theme-orange;  }
            .svg-icon {
                .svg-fill {  fill: $theme-orange;  }
                .svg-stroke {  stroke: $theme-orange;  }
            }
        }
        &.active {
            .x-nested-nav {
                padding-left: 36px;
                background-color: $grey-5;
                overflow: hidden;
                .x-nested-nav-item {
                    .item-link {
                        color: $theme-white;
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
    .collapse .x-nested-nav {
        overflow: visible;
        .x-nested-nav-item {
            overflow: hidden;
            .item-link span {
                transition: all ease-in 0.2s;
                opacity: 0;
            }
            .x-nested-nav.collapse {
                display: none;
            }
            &:hover {
                overflow: visible;
                position: relative;
                .x-nested-nav.collapse {
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