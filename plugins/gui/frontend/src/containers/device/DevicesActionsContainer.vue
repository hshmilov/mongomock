<template>
    <x-data-action-menu module="devices" :selected="devices" @done="$emit('done')">
        <x-data-action-item :handle-save="saveDeploy" message="Deployment initiated" title="Deploy..." action-text="Deploy">
            <h3 class="mb-2">Deploy Executable</h3>
            <x-schema-form :schema="deployFormSchema" v-model="deploy.data" api-upload="actions"
                           @validate="deploy.valid = $event" />
        </x-data-action-item>
        <x-data-action-item :handle-save="saveRun" message="Started running" title="Run..." action-text="Run">
            <h3 class="mb-2">Run Command</h3>
            <x-schema-form :schema="shellFormSchema" v-model="run.data" class="expand" @validate="run.valid = $event"/>
        </x-data-action-item>
        <x-data-action-item :handle-save="saveBlacklist" message="Blacklist saved" title="Blacklist..." action-text="Blacklist">
            <div>Add {{devices.length}} devices to Blacklist?</div>
            <div>These devices will be prevented from executing code on.</div>
        </x-data-action-item>
    </x-data-action-menu>
</template>

<script>
    import xDataActionMenu from '../../components/data/DataActionMenu.vue'
    import xDataActionItem from '../../components/data/DataActionItem.vue'
    import xSchemaForm from '../../components/schema/SchemaForm.vue'

    import { mapActions } from 'vuex'
    import { ADD_DATA_LABELS, RUN_ACTION } from '../../store/actions'

	export default {
		name: 'devices-actions-container',
		components: {
			xDataActionMenu, xDataActionItem, xSchemaForm
		},
		props: {'devices': {required: true}},
        computed: {
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
            }
        },
		data () {
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
            ...mapActions({ addLabels: ADD_DATA_LABELS, runAction: RUN_ACTION }),
			saveBlacklist () {
				/*
				Blacklist is currently implemented by checking for a designated tag,
				Therefore, adding this tag to selected devices
				 */
                return this.addLabels({module: 'devices', data: {entities: this.devices, labels: ['do_not_execute']}})
			},
			saveDeploy () {
				return new Promise((resolve, reject) => {
            	    if (!this.deploy.valid) reject()
					this.runAction({type: 'deploy', data: { ...this.deploy.data, internal_axon_ids: this.devices}})
						.then((response) => {
							this.deploy.data = {}
							resolve(response)
						})
						.catch(error => reject(error.response.data))
				})
			},
			saveRun () {
				return new Promise((resolve, reject) => {
				    if (!this.run.valid) reject()
					this.runAction({type: 'shell', data: { ...this.run.data, internal_axon_ids: this.devices}})
						.then(response => resolve(response))
                        .catch(error => reject(error.response.data))
				})
			}
		}
	}
</script>

<style lang="scss">
    .schema-form.expand .item {
        width: 100%;
        .object {
            width: 100%;
        }
    }
</style>