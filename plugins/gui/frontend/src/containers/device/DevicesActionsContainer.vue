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
                <searchable-checklist title="Tag as:" :items="device.labelList.data" :searchable="true"
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
    import TagsMixin from './tags'
	import { mapState } from 'vuex'

	export default {
		name: 'devices-actions-container',
		components: {
			TriggerableDropdown, FeedbackModal, DynamicPopover, SearchableChecklist,
			'nested-menu': NestedMenu, 'nested-menu-item': NestedMenuItem
		},
		props: {'devices': {required: true}},
        mixins: [TagsMixin],
        computed: {
			...mapState(['device']),
			deviceById () {
				if (!this.device.deviceList.data || !this.device.deviceList.data.length) return {}

				return this.device.deviceList.data.filter((device) => {
					return this.devices.includes(device.id)
				}).reduce(function (map, input) {
					map[input.id] = input
					return map
				}, {})
			},
			currentTags () {
				if (!this.devices || !this.devices.length || !this.deviceById[this.devices[0]]) { return [] }
				let labels = this.deviceById[this.devices[0]].labels
				if (this.devices.length === 1) { return labels }
				this.devices.forEach((device) => {
					let deviceLabels = this.deviceById[device].labels
					if (!deviceLabels || !deviceLabels.length) {
						labels = []
						return
					}
					labels = labels.filter((label) => {
						return deviceLabels.includes(label)
					})
				})
				return labels
			}
        },
		data () {
			return {
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
            activate(module) {
				module.isActive = true
                // Close the actions dropdown
                this.$el.click()
            },
			saveBlacklist () {
				/*
				Blacklist is currently implemented by checking for a designated tag,
				Therefore, adding this tag to selected devices
				 */
                return this.addDeviceLabels({devices: this.devices, tags: ['do_not_execute']})
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
		}
	}
</script>

<style lang="scss">

</style>