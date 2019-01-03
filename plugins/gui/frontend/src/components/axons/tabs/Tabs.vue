<template>
    <div class="x-tabs" :class="{ vertical }">
        <ul class="header">
            <li v-for="tab in tabs" v-if="tab.id !== undefined" @click="selectTab(tab.id)" :id="tab.id"
                class="header-tab" :class="{active: tab.isActive, disabled: tab.outdated}">
                <x-logo-name v-if="tab.logo" :name="tab.title"/>
                <div v-else>{{ tab.title }}</div>
            </li>
        </ul>
        <div class="body">
            <slot></slot>
        </div>
    </div>
</template>

<script>
    import xLogoName from '../visuals/LogoName.vue'

    export default {
        name: 'x-tabs',
        components: {xLogoName},
        props: {vertical: {default: false}},
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
        },
        updated() {
            this.$emit('updated')
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

        .body {
            height: calc(100% - 48px);
            background-color: $theme-white;
            border-top: 0;
            border-bottom-right-radius: 4px;
            border-bottom-left-radius: 4px;
            padding: 12px;
            overflow: auto;
        }

        &.vertical {
            display: flex;

            > .header {
                display: block;
                border-right: 2px solid $grey-1;
                overflow: auto;
                margin-left: -12px;
                width: 200px;

                .header-tab {
                    padding: 24px;
                    background: $theme-white;
                    white-space: pre-line;

                    &:after {
                        content: none;
                    }

                    &.active {
                        background-color: $grey-1;
                    }

                    .title {
                        white-space: pre-line;
                    }
                }
            }

            .body {
                flex: 1 0 auto;
                height: calc(100% - 24px);
                width: calc(100% - 200px);
            }
        }
    }
</style>