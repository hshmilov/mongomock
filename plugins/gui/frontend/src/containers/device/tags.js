import { mapActions } from 'vuex'
import {
	CREATE_DEVICE_LABELS,
	DELETE_DEVICE_LABELS
} from '../../store/modules/device'

export default {
	watch: {
		currentTags(newLabels) {
			this.tag.selected = newLabels
		}
	},
	data() {
		return {
			tag: {
				isActive: false,
				selected: []
			},
		}
	},
	methods: {
		...mapActions({
			addDeviceLabels: CREATE_DEVICE_LABELS,
			removeDeviceLabels: DELETE_DEVICE_LABELS
		}),
		saveTags () {
			/* Separate added and removed tags and create an uber promise returning after both are updated */

			let added = this.tag.selected.filter((tag) => {
				return (!this.currentTags.includes(tag))
			})
			let removed = this.currentTags.filter((tag) => {
				return (!this.tag.selected.includes(tag))
			})
			return Promise.all([this.addDeviceLabels({devices: this.devices, labels: added}),
				this.removeDeviceLabels({devices: this.devices, labels: removed})])

		}
	}
}