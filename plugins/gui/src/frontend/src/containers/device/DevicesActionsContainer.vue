<template>
    <div>
        <triggerable-dropdown size="sm" align="right">
            <div slot="dropdownTrigger" class="link">Actions</div>
            <nested-menu slot="dropdownContent">
                <nested-menu-item title="Tag..." @click="activate(tag)"></nested-menu-item>
                <nested-menu-item title="Add to Black List" @click="activate(blacklist)"></nested-menu-item>
                <!--<nested-menu-item title="Block" @click="activate(block)">-->
                    <!--<dynamic-popover size="xs" left="236">-->
                        <!--<nested-menu>-->
                            <!--<nested-menu-item v-for="blocker, index in block.blockers" :key="index" :title="blocker"-->
                                              <!--@click="block.selected = blocker"></nested-menu-item>-->
                        <!--</nested-menu>-->
                    <!--</dynamic-popover>-->
                <!--</nested-menu-item>-->
                <!--<nested-menu-item title="Scan with" @click="activate(scan)">-->
                    <!--<dynamic-popover size="xs" left="236">-->
                        <!--<nested-menu>-->
                            <!--<nested-menu-item v-for="scanner, index in scan.scanners" :key="index" :title="scanner"-->
                                              <!--@click="scan.selected = scanner"></nested-menu-item>-->
                        <!--</nested-menu>-->
                    <!--</dynamic-popover>-->
                <!--</nested-menu-item>-->
                <!--<nested-menu-item title="Deploy" @click="activate(deploy)">-->
                    <!--<dynamic-popover size="xs" left="236">-->
                        <!--<nested-menu>-->
                            <!--<nested-menu-item v-for="deployment, index in deploy.deployments" :key="index" :title="deployment"-->
                                              <!--@click="deploy.selected = deployment"></nested-menu-item>-->
                        <!--</nested-menu>-->
                    <!--</dynamic-popover>-->
                <!--</nested-menu-item>-->
            </nested-menu>
        </triggerable-dropdown>
        <feedback-modal v-model="tag.isActive" :handleSave="saveTags" :message="`Tagged ${devices.length} devices!`">
                <searchable-checklist title="Tag as:" :items="device.tagList.data" :searchable="true"
                                      :extendable="true" v-model="tag.selected"></searchable-checklist>
        </feedback-modal>
        <feedback-modal v-model="blacklist.isActive" :handleSave="saveBlacklist" message="Blacklist saved">
            <div>Add {{devices.length}} devices to Blacklist?</div>
            <div>These devices will be prevented from executing code on.</div>
        </feedback-modal>
        <feedback-modal v-model="block.isActive" :handleSave="saveBlock" message="Block saved">
            <div>Block {{devices.length}} devices by {{block.selected}}?</div>
        </feedback-modal>
        <feedback-modal v-model="scan.isActive" :handleSave="saveScan" message="Scan saved">
            <div>Scan {{devices.length}} devices with {{scan.selected}} scanner?</div>
        </feedback-modal>
        <feedback-modal v-model="deploy.isActive" :handleSave="saveDeploy" message="Deploy saved">
            <div>Deploy {{deploy.selected}} on {{devices.length}} devices?</div>
        </feedback-modal>
    </div>
</template>

<script>
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
	import NestedMenu from '../../components/menus/NestedMenu.vue'
	import NestedMenuItem from '../../components/menus/NestedMenuItem.vue'
	import FeedbackModal from '../../components/popover/FeedbackModal.vue'
	import DynamicPopover from '../../components/popover/DynamicPopover.vue'
	import SearchableChecklist from '../../components/SearchableChecklist.vue'

	import { mapState, mapActions } from 'vuex'
	import {
		CREATE_DEVICE_TAGS,
		DELETE_DEVICE_TAGS
	} from '../../store/modules/device'

	export default {
		name: 'devices-actions-container',
		props: {'devices': {required: true}},
		components: {
			TriggerableDropdown, FeedbackModal, DynamicPopover, SearchableChecklist,
			'nested-menu': NestedMenu, 'nested-menu-item': NestedMenuItem
		},
		computed: {
			...mapState(['device']),
			deviceById () {
				return this.device.deviceList.data.filter((device) => {
					return this.devices.includes(device.id)
				}).reduce(function (map, input) {
					map[input.id] = input
					return map
				}, {})
			},
			currentTags () {
				if (!this.devices || !this.devices.length || !this.deviceById[this.devices[0]]) { return [] }
				let tags = this.deviceById[this.devices[0]]['tags.name']
                if (this.devices.length === 1) { return tags }
				this.devices.forEach((device) => {
					let deviceTags = this.deviceById[device]['tags.name']
					if (!deviceTags || !deviceTags.length) {
						tags = []
					}
					tags = tags.filter((tag) => {
						return deviceTags.includes(tag)
                    })
				})
				return tags
			}
		},
        watch: {
			currentTags(newTags) {
				this.tag.selected = newTags
            }
        },
		data () {
			return {
				tag: {
					isActive: false,
					selected: []
				},
                blacklist: {
					isActive: false
                },
                block: {
					isActive: false,
                    blockers: ['Cisco'],
                    selected: ''
                },
                scan: {
					isActive: false,
				    scanners: ['Qualys', 'Nexpose', 'Nessus'],
                    selected: ''
                },
                deploy: {
					isActive: false,
				    deployments: ['ePO (WIN 5.3.2)', 'ePO (OSX 4.8.1938)', 'Qualys (LIN 1.6.1.26)', 'Qualys (WIN 1.6.0.246)'],
                    selected: ''
                },
			}
		},
		methods: {
			...mapActions({
				addDeviceTags: CREATE_DEVICE_TAGS,
				removeDeviceTags: DELETE_DEVICE_TAGS
			}),
            activate(module) {
				module.isActive = true
                // Close the actions dropdown
                this.$el.click()
            },
			saveTags () {
				/* Separate added and removed tags and create an uber promise returning after both are updated */

                let added = this.tag.selected.filter((tag) => {
					return (!this.currentTags.includes(tag))
				})
                let removed = this.currentTags.filter((tag) => {
					return (!this.tag.selected.includes(tag))
				})
				return Promise.all([this.addDeviceTags({devices: this.devices, tags: added}),
					this.removeDeviceTags({devices: this.devices, tags: removed})])

			},
			saveBlacklist () {
				/*
				Blacklist is currently implemented by checking for a designated tag,
				Therefore, adding this tag to selected devices
				 */
                return this.addDeviceTags({devices: this.devices, tags: ['do_not_execute']})
			},
			saveBlock () {
				return new Promise((resolve, reject) => {
					resolve()
				})
			},
			saveScan () {
				return new Promise((resolve, reject) => {
					resolve()
				})
			},
			saveDeploy () {
				return new Promise((resolve, reject) => {
					resolve()
				})
			}
		},
        mounted() {
			this.tag.selected = this.currentTags
        }
	}
</script>

<style lang="scss">

</style>