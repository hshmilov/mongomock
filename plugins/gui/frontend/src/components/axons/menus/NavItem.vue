<template>
    <router-link tag="li" :to="disabled? {}: link" :id="id" @click.native="onClick"
                 class="x-nav-item" :class="{ disabled }"
                 :active-class="activeClass" :exact-active-class="exactActiveClass">
        <button class="item-link" :title="disabled? undefined : name">
            <svg-icon v-if="icon" :name="`navigation/${icon}`" width="24" :original="true" />
            <div v-else class="empty-icon"></div>
            <span>{{ name }}</span>
        </button>
        <slot/>
    </router-link>
</template>

<script>
    export default {
		name: 'x-nav-item',
		props: [ 'name', 'path', 'icon', 'exact', 'disabled', 'id', 'clickHandler' ],
        computed: {
            link() {
            	if (this.path) return { path: this.path }
            	return { name: this.name }
            },
            activeClass() {
                if (!this.disabled && !this.exact) {
                    return 'active'
                }
                return ''
            },
            exactActiveClass() {
                if (!this.disabled && this.exact) {
                    return 'active'
                }
                return ''
            }
        },
        methods: {
		    onClick() {
		        if (this.clickHandler) {
		            this.clickHandler(this.name)
                }
                this.$emit('click')
            }
        }
    }
</script>

<style lang="scss">
    .x-nav-item {
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
            .empty-icon {
                width: 35px;
                display: inline-block;
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
                .x-nav-item {
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
    .x-side-bar.collapse .x-nav {
        overflow: visible;
        .x-nav-item {
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
                overflow: visible;
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