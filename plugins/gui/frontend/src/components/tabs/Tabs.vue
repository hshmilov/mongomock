<template>
    <div class="tabs">
        <div class="tabs-header">
            <ul class="nav nav-tabs">
                <li v-for="tab in tabs" class="nav-item">
                    <a class="nav-link" :class="{active: tab.isActive, disabled: tab.outdated}" @click="selectTab(tab)">
                        <img v-if="tab.logo" :src="`/src/assets/images/logos/${tab.logo}.png`" class="img-md" />
                        {{ tab.title }}
                    </a>
                </li>
            </ul>
        </div>
        <div class="tab-content">
            <slot></slot>
        </div>
    </div>
</template>

<script>
	export default {
		name: 'tabs',
        props: [],
        data() {
			return {
				tabs: []
            }
        },
        methods: {
			selectTab(selectedTab) {
				this.tabs.forEach((tab) => {
					tab.isActive = (tab.id === selectedTab.id)
                })
            }
        },
		created() {
			this.tabs = this.$children
		}
	}
</script>

<style scoped lang="scss">
    .nav-item:hover > .nav-link {
        color: $theme-orange;
    }
    .tab-content {
        background-color: $theme-white;
        border: 1px solid $grey-2;
        border-top: 0;
        border-bottom-right-radius: 4px;
        border-bottom-left-radius: 4px;
        padding: 12px;
    }
</style>