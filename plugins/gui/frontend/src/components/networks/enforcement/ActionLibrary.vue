<template>
    <div class="x-action-library">
        <x-search-input v-model="searchValue" />
        <md-list class="actions-container" :md-expand-single="true">
            <md-list-item :md-expand="true" v-for="category in categories" :key="category" v-if="getItems(category).length">
                <x-title :logo="`actions/${category}`">{{ getTitle(category) }}</x-title>
                <md-list slot="md-expand" v-if="getItems(category).length">
                    <md-list-item v-for="action in getItems(category)" :key="action" @click="onClickAction(action)">
                        <x-title :logo="`actions/${action}`" :disabled="disabled(action)">{{ getTitle(action) }}</x-title>
                        <img v-if="disabled(action)" :src="require('Logos/actions/lock.png')" height="24" class="md-image" />
                    </md-list-item>
                </md-list>
            </md-list-item>
        </md-list>
    </div>
</template>

<script>
    import xTitle from '../../axons/layout/Title.vue'
    import xSearchInput from '../../neurons/inputs/SearchInput.vue'
    import actionsMixin from '../../../mixins/actions'
    import {actionsMeta} from '../../../constants/enforcement'

    export default {
        name: 'x-action-library',
        components: {
            xTitle, xSearchInput
        },
        mixins: [actionsMixin],
        props: {
            categories: {
                type: Array,
                required: true
            }
        },
        data() {
            return {
                searchValue: ''
            }
        },
        methods: {
            getTitle(name) {
                return actionsMeta[name].title
            },
            getItems(name) {
                return actionsMeta[name].items
                    .filter(action => this.getTitle(action).toLowerCase().includes(this.searchValue.toLowerCase()))
            },
            disabled(action) {
               return !this.actionsDef[action]
            },
            onClickAction(name) {
                this.checkEmptySettings(name)
                if (this.anyEmptySettings || this.disabled(name)) return
                this.$emit('select', name)
            }
        }
    }
</script>

<style lang="scss">
    .x-action-library {
        .actions-container {
            overflow: auto;
            height: calc(100% - 36px);
            .x-title {
                .md-image {
                    height: 36px;
                }
            }
            .md-list-expand {
                margin-left: 36px;
            }
        }
    }
</style>