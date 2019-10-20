<template>
  <div class="x-spaces">
    <x-tabs
      v-if="spaces.length"
      ref="tabs"
      :extendable="!isReadOnly"
      remove-text="Remove Space"
      @add="addNewSpace"
      @rename="renameSpace"
      @remove="removeSpace"
      @click="selectSpace"
    >
      <x-tab
        :id="defaultSpace.uuid"
        :title="defaultSpace.name"
        :selected="currentSpace === defaultSpace.uuid"
        :editable="!isReadOnly"
      >
        <x-default-space
          v-if="active"
          slot-scope="{ active }"
          :panels="defaultSpace.panels"
          @add="() => addNewPanel(defaultSpace.uuid)"
          @edit="editPanel"
        />
      </x-tab>
      <x-tab
        v-if="!isReadOnly"
        :id="personalSpace.uuid"
        :title="personalSpace.name"
        :selected="currentSpace === personalSpace.uuid"
      >
        <x-panels
          v-if="active"
          slot-scope="{ active }"
          :panels="personalSpace.panels"
          @add="() => addNewPanel(personalSpace.uuid)"
          @edit="editPanel"
        />
      </x-tab>
      <x-tab
        v-for="space in customSpaces"
        :id="space.uuid"
        :key="space.uuid"
        :title="space.name"
        :selected="currentSpace === space.uuid"
        :editable="!isReadOnly"
        :removable="!isReadOnly"
      >
        <x-panels
          v-if="active"
          slot-scope="{ active }"
          :panels="space.panels"
          @add="() => addNewPanel(space.uuid, true)"
          @edit="editPanel"
        />
      </x-tab>
      <div slot="remove_confirm">
        <div>This space will be completely removed from the system and</div>
        <div>no other user will be able to use it.</div>
        <div>Removing the space is an irreversible action.</div>
      </div>
    </x-tabs>
    <x-wizard
      v-if="wizard.active"
      :space="wizard.space"
      :custom-space="editCustomSpace"
      :panel="wizard.panel"
      @close="closeWizard"
    />
  </div>
</template>

<script>
  import xTabs from '../../axons/tabs/Tabs.vue'
  import xTab from '../../axons/tabs/Tab.vue'
  import xDefaultSpace from './DefaultSpace.vue'
  import xPanels from './Panels.vue'
  import xWizard from '../../networks/dashboard/Wizard.vue'

  import {mapState, mapMutations, mapActions} from 'vuex'
  import {
    SAVE_DASHBOARD_SPACE, CHANGE_DASHBOARD_SPACE, REMOVE_DASHBOARD_SPACE,
    SET_CURRENT_SPACE
  } from '../../../store/modules/dashboard'

  export default {
    name: 'XSpaces',
    components: {
      xTabs, xTab, xDefaultSpace, xPanels, xWizard
    },
    props: {
      spaces: {
        type: Array,
        required: true
      }
    },
    data() {
      return {
        wizard: {
          active: false,
          space: ''
        },
        processing: false,
        editCustomSpace: false,
      }
    },
    computed: {
      ...mapState({
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Dashboard === 'ReadOnly'
        },
        currentSpace (state) {
          return state.dashboard.currentSpace || this.defaultSpace.uuid
        }
      }),
      defaultSpace() {
        return this.spaces.find(space => space.type === 'default')
      },
      personalSpace() {
        return this.spaces.find(space => space.type === 'personal')
      },
      customSpaces() {
        return this.spaces.filter(space => space.type === 'custom')
      },
      newSpaceName() {
        for (let i = this.customSpaces.length - 1; i >= 0; i--) {
          let matches = this.customSpaces[i].name.match('Space (\\d+)')
          if (matches && matches.length > 1) {
            return `Space ${parseInt(matches[1]) + 1}`
          }
        }
        return 'Space 1'
      }
    },
    methods: {
      ...mapMutations({
        selectSpace: SET_CURRENT_SPACE
      }),
      ...mapActions({
        saveSpace: SAVE_DASHBOARD_SPACE,
        renameSpace: CHANGE_DASHBOARD_SPACE,
        removeSpace: REMOVE_DASHBOARD_SPACE
      }),
      addNewPanel (spaceId, isCustomSpace) {
        this.editCustomSpace = isCustomSpace
        this.wizard.active = true
        this.wizard.space = spaceId
      },
      closeWizard () {
        this.wizard.active = false
        this.wizard.space = ''
        this.wizard.panel = null
        this.editCustomSpace = false
      },
      editPanel (panel) {
        this.wizard.active = true
        this.wizard.panel = { ...panel }
      },
      addNewSpace () {
        if (this.processing) return
        this.processing = true
        this.saveSpace(this.newSpaceName).then(spaceId => {
          this.$nextTick(() => {
            this.$refs.tabs.renameTabById(spaceId)
            this.$refs.tabs.selectTab(spaceId)
            this.processing = false
          })
        })
      }
    }
  }
</script>

<style lang="scss">
    .x-spaces {
        height: calc(100% - 42px);
    }
</style>