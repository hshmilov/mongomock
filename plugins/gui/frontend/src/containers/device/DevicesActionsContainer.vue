<template>
    <x-data-action-menu module="device" :selected="devices">
        <x-data-action-item :handle-save="saveDeploy" message="Deployment initiated" title="Deploy...">
            <h3 class="mb-2">Deploy Executable</h3>
            <x-schema-form :schema="deployFormSchema" @validate="deploy.valid = $event" />
        </x-data-action-item>
        <x-data-action-item :handle-save="saveRun" message="Started running" title="Run...">
            <h3 class="mb-2">Run Command</h3>
            <x-schema-form :schema="runFormSchema" class="expand" @validate="run.valid = $event"/>
        </x-data-action-item>
        <x-data-action-item :handle-save="saveBlacklist" message="Blacklist saved" title="Blacklist...">
            <div>Add {{devices.length}} devices to Blacklist?</div>
            <div>These devices will be prevented from executing code on.</div>
        </x-data-action-item>
    </x-data-action-menu>
</template>

<script>
    import xDataActionMenu from '../../components/data/DataActionMenu.vue'
    import xDataActionItem from '../../components/data/DataActionItem.vue'
    import xSchemaForm from '../../components/schema/SchemaForm.vue'

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
                        	name: 'exe_file',
                            title: 'File To Execute',
                        	type: 'array',
                            format: 'bytes',
                            items: {
                        		type: 'integer', default: 0
                            }
                        },
                        {
                        	name: 'exe_params',
                            title: 'Command Line Parameters',
                            type: 'string'
                        }
                    ],
                    required: ['exe_file']
                }
            },
            runFormSchema() {
				return {
					type: 'array',
					items: [
						{
							name: 'command_line',
							title: 'Command Line',
							type: 'string'
						}
					],
					required: ['command_line']
				}
            }
        },
		data () {
			return {
                deploy: {
                    selected: '',
                    valid: false
                },
                run: {
                    valid: true
                }
			}
		},
		methods: {
			saveBlacklist () {
				/*
				Blacklist is currently implemented by checking for a designated tag,
				Therefore, adding this tag to selected devices
				 */
                return this.addLabels({devices: this.devices, tags: ['do_not_execute']})
			},
			saveDeploy () {
				return new Promise((resolve, reject) => {
            	    if (!this.deploy.valid) reject()
					resolve()
				})
			},
			saveRun () {
				return new Promise((resolve, reject) => {
				    if (!this.run.valid) reject()
					resolve()
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