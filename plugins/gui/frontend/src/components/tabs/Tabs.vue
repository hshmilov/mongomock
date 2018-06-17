<template>
    <div class="x-tabs">
        <ul class="header">
            <li v-for="tab in tabs" v-if="tab.id !== undefined" @click="selectTab(tab.id)" :id="tab.id"
                class="header-tab" :class="{active: tab.isActive, disabled: tab.outdated}">
                <x-logo-name v-if="tab.logo" :name="tab.title" />
                <div v-else>{{ tab.title }}</div>
            </li>
        </ul>
        <div class="content">
            <slot></slot>
        </div>
    </div>
</template>

<script>
    import xLogoName from '../titles/LogoName.vue'

	export default {
		name: 'x-tabs',
        components: {xLogoName},
        data() {
			return {
				tabs: []
            }
        },
        methods: {
			selectTab(selectedId) {
				let found = false
				this.tabs.forEach((tab) => {
					tab.isActive = (tab.id === selectedId)
                    if (tab.isActive) found = true
                })
                if (!found) {
					this.tabs[0].isActive = true
                }
                this.$emit('click', selectedId)
            }
        },
		created() {
			this.tabs = this.$children
		}
	}
</script>

<style lang="scss">
    .x-tabs {
        .header {
            list-style: none;
            display: flex;
            overflow-y: hidden;
            .header-tab {
                position: relative;
                padding: 12px 24px 12px 48px;
                background: $grey-2;
                display: flex;
                white-space: nowrap;
                cursor: pointer;
                img {
                    margin-right: 4px;
                }
                &.active {
                    background: $theme-white;
                    z-index: 100;
                    &:after {
                        background: $theme-white;
                    }
                }
                &:hover {
                    text-shadow: $text-shadow;
                }
                &:after {
                    content: '';
                    position: absolute;
                    background: $grey-2;
                    height: 52px;
                    width: 24px;
                    right: -16px;
                    z-index: 20;
                    top: -1px;
                    transform: rotate(-15deg);
                    border-top-right-radius: 50%;
                }
            }
        }

        .content {
            background-color: $theme-white;
            border-top: 0;
            border-bottom-right-radius: 4px;
            border-bottom-left-radius: 4px;
            padding: 12px;
        }
    }
</style>