<template>
    <div class="data-view-menu">
        <triggerable-dropdown :arrow="false" align="right" size="lg">
            <div slot="trigger" class="link">View</div>
            <nested-menu slot="content">
                <nested-menu-item title="Save Current" @click="openSaveView" />
                <template v-if="views && views.length">
                    <div class="title">Saved Views</div>
                    <div class="content">
                        <nested-menu-item v-for="{name, view} in views" :key="name" :title="name"
                                          @click="updateModuleView(view)"/>
                    </div>
                </template>
            </nested-menu>
        </triggerable-dropdown>
        <modal v-if="saveModal.isActive" @close="closeSaveView" approveText="save" @confirm="confirmSaveView">
            <div slot="body" class="form-group">
                <label class="form-label" for="saveName">Save as:</label>
                <input class="form-control" v-model="saveModal.name" id="saveName" @keyup.enter="confirmSaveView">
            </div>
        </modal>
    </div>
</template>

<script>
	import Modal from '../../components/popover/Modal.vue'
	import TriggerableDropdown from '../../components/popover/TriggerableDropdown.vue'
	import NestedMenu from '../../components/menus/NestedMenu.vue'
	import NestedMenuItem from '../../components/menus/NestedMenuItem.vue'
	import DynamicPopover from '../../components/popover/DynamicPopover.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
    import { UPDATE_DATA_VIEW } from '../../store/mutations'
	import { FETCH_DATA_VIEWS, SAVE_DATA_VIEW } from '../../store/actions'

	export default {
		name: 'x-data-view-menu',
        components: { Modal, TriggerableDropdown, NestedMenu, NestedMenuItem, DynamicPopover },
        props: { module: {required: true} },
        computed: {
			...mapState({
				views (state) {
					return state[this.module].views.data
				}
			})
        },
        data() {
			return {
				saveModal: {
					isActive: false,
                    name: ''
                }
            }
        },
        methods: {
            ...mapMutations({
                updateView: UPDATE_DATA_VIEW
            }),
            ...mapActions({
				saveView: SAVE_DATA_VIEW,
                fetchViews: FETCH_DATA_VIEWS
            }),
			updateModuleView(view) {
				this.updateView({module: this.module, view})
			},
			openSaveView() {
				this.saveModal.isActive = true
            },
			confirmSaveView () {
				if (!this.saveModal.name) return

				this.saveView({
					module: this.module, name: this.saveModal.name
				}).then(() => this.saveModal.isActive = false)
			},
            closeSaveView() {
				this.saveModal.isActive = false
            }
        },
        created() {
			this.fetchViews({ module: this.module }).then(() => {
                if (this.$route.query.view) {
                    let requestedView = this.views.filter(view => view.name === this.$route.query.view)
                    if (requestedView && requestedView.length) {
                    	this.updateModuleView(requestedView[0].view)
                    }
                }
            })
        }
	}
</script>

<style lang="scss">
    .data-view-menu {
        .menu {
            .title {
                font-size: 12px;
                font-weight: 400;
                text-transform: uppercase;
                padding-left: 6px;
                margin-top: 6px;
            }
            .content {
                max-height: 40vh;
                overflow: auto;
            }
        }
    }
</style>