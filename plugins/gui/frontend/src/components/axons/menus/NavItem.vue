<template>
  <router-link
    :id="id"
    tag="li"
    :to="disabled? {}: link"
    class="x-nav-item"
    :class="{ disabled }"
    :active-class="activeClass"
    :exact-active-class="exactActiveClass"
    @click.native="onClick"
  >
    <button
      class="item-link"
      :title="name"
    >
      <md-icon
        v-if="icon"
        :md-src="`/src/assets/icons/navigation/${icon}.svg`"
      />
      <div
        v-else
        class="empty-icon"
      />
      <div class="menu-title">{{ title || name }}</div>
    </button>
    <slot />
  </router-link>
</template>

<script>
    export default {
		name: 'XNavItem',
		props: [ 'name', 'path', 'title', 'icon', 'exact', 'disabled', 'id', 'clickHandler' ],
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
            .md-icon {
                transition: all ease-in 0.2s;
                margin-right: 10px;
                display: inline-block;
                .svg-fill {  fill: $grey-4  }
                .svg-stroke {  stroke: $grey-4  }
            }
            .empty-icon {
                width: 35px;
                display: inline-block;
            }
            .menu-title {
                transition: all ease-in 0.2s;
                display: inline-block;
                line-height: 20px;
            }
        }
        &.disabled {
            .md-icon {
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
            .md-icon {
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
        padding-left: 0px;
        .x-nav-item {
            overflow: hidden;
            .item-link .menu-title {
                opacity: 0;
                transform: translateX(-200px);
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
                    .item-link .menu-title {
                        opacity: 1;
                    }
                }
            }
        }
    }
</style>