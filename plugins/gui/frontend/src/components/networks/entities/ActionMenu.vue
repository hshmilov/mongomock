<template>
    <x-action-menu :module="module" :entities="entities" @done="$emit('done')">
        <template v-if="module === 'devices'">
            <x-action-menu-item :handle-save="saveDeploy" message="Deployment initiated" title="Deploy..."
                                action-text="Deploy">
                <h3 class="mb-2">Deploy Executable</h3>
                <x-form :schema="deployFormSchema" v-model="deploy.data" api-upload="actions"
                        @validate="deploy.valid = $event"/>
            </x-action-menu-item>
            <x-action-menu-item :handle-save="saveRun" message="Started running" title="Run..." action-text="Run">
                <h3 class="mb-2">Run Command</h3>
                <x-form :schema="shellFormSchema" v-model="run.data" class="expand" @validate="run.valid = $event"/>
            </x-action-menu-item>
            <x-action-menu-item :handle-save="saveBlacklist" message="Blacklist saved" title="Blacklist..."
                                action-text="Blacklist">
                <div>Add {{ selectionCount }} devices to Blacklist?</div>
                <div>These devices will be prevented from executing code on.</div>
            </x-action-menu-item>
        </template>
    </x-action-menu>
</template>

<script>
    import xActionMenu from '../../neurons/data/ActionMenu.vue'
    import xActionMenuItem from '../../neurons/data/ActionMenuItem.vue'
    import xForm from '../../neurons/schema/Form.vue'

    import {mapState, mapActions} from 'vuex'
    import {ADD_DATA_LABELS, RUN_ACTION} from '../../../store/actions'

    export default {
        name: 'x-entities-action-menu',
        components: {xActionMenu, xActionMenuItem, xForm},
        props: {module: {required: true}, entities: {}},
        computed: {
            ...mapState({
                dataCount(state) {
                    return state[this.module].count.data
                }
            }),
            deployFormSchema() {
                return {
                    type: 'array',
                    items: [
                        {
                            name: 'action_name',
                            title: 'Action Name',
                            type: 'string'
                        },
                        {
                            name: 'binary',
                            title: 'File To Execute',
                            type: 'file'
                        },
                        {
                            name: 'params',
                            title: 'Command Line Parameters',
                            type: 'string'
                        }
                    ],
                    required: ['action_name', 'binary']
                }
            },
            shellFormSchema() {
                return {
                    type: 'array',
                    items: [
                        {
                            name: 'action_name',
                            title: 'Action Name',
                            type: 'string'
                        },
                        {
                            name: 'command',
                            title: 'Command Line',
                            type: 'string'
                        }
                    ],
                    required: ['action_name', 'command']
                }
            },
            selectionCount() {
                if (this.entities.include === undefined || this.entities.include) {
                    return this.entities.ids.length
                }
                return this.dataCount - this.entities.ids.length
            }
        },
        data() {
            return {
                deploy: {
                    valid: false,
                    data: {}
                },
                run: {
                    valid: true,
                    data: {}
                }
            }
        },
        methods: {
            ...mapActions({addLabels: ADD_DATA_LABELS, runAction: RUN_ACTION}),
            saveBlacklist() {
                /*
                Blacklist is currently implemented by checking for a designated tag,
                Therefore, adding this tag to selected devices
                 */
                return this.addLabels({
                    module: 'devices', data: {
                        entities: this.entities, labels: ['do_not_execute']
                    }
                })
            },
            saveDeploy() {
                return new Promise((resolve, reject) => {
                    if (!this.deploy.valid) reject()
                    this.runAction({
                        type: 'deploy', data: {
                            ...this.deploy.data, entities: this.entities
                        }
                    }).then((response) => {
                        this.deploy.data = {}
                        resolve(response)
                    }).catch(error => reject(error.response.data))
                })
            },
            saveRun() {
                return new Promise((resolve, reject) => {
                    if (!this.run.valid) reject()
                    this.runAction({
                        type: 'shell', data: {
                            ...this.run.data, entities: this.entities
                        }
                    }).then(response => {
                        this.run.data = {}
                        resolve(response)
                    }).catch(error => reject(error.response.data))
                })
            }
        }
    }
</script>

<style lang="scss">
    .x-form.expand .item {
        width: 100%;

        .object {
            width: 100%;
        }
    }
</style>