<template>
  <div class="x-spaces">
    <x-tabs
      v-if="spaces.length"
      :extendable="!isReadOnly"
      @add="addNewSpace"
      @rename="renameSpace"
      @remove="removeSpace"
      ref="tabs"
    >
      <x-tab
        :id="personalSpace.uuid"
        :title="personalSpace.name"
      >
        <x-panels
          slot-scope="{ active }"
          v-if="active"
          :panels="personalSpace.panels"
          @add="() => addNewPanel(personalSpace.uuid)"
        />
      </x-tab>
      <x-tab
        :id="defaultSpace.uuid"
        :title="defaultSpace.name"
        :selected="true"
        :editable="!isReadOnly"
      >
        <x-default-space
          slot-scope="{ active }"
          v-if="active"
          :panels="defaultSpace.panels"
          @add="() => addNewPanel(defaultSpace.uuid)"
        />
      </x-tab>
      <x-tab
        v-for="space in customSpaces"
        :id="space.uuid"
        :key="space.uuid"
        :title="space.name"
        :editable="!isReadOnly"
        :removable="!isReadOnly"
      >
        <x-panels
          slot-scope="{ active }"
          v-if="active"
          :panels="space.panels"
          @add="() => addNewPanel(space.uuid)"
        />
      </x-tab>
    </x-tabs>
    <x-wizard
      v-if="wizard.active"
      :space="wizard.space"
      @done="finishNewPanel"
    />
  </div>
</template>

<script>
  import xTabs from '../../axons/tabs/Tabs.vue'
  import xTab from '../../axons/tabs/Tab.vue'
  import xDefaultSpace from './DefaultSpace.vue'
  import xPanels from './Panels.vue'
  import xWizard from '../../networks/dashboard/Wizard.vue'

  import {mapState, mapActions} from 'vuex'
  import {
    SAVE_DASHBOARD_SPACE, CHANGE_DASHBOARD_SPACE, REMOVE_DASHBOARD_SPACE
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
        }
      }
    },
    computed: {
      ...mapState({
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Dashboard === 'ReadOnly'
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
      ...mapActions({
        saveSpace: SAVE_DASHBOARD_SPACE,
        renameSpace: CHANGE_DASHBOARD_SPACE,
        removeSpace: REMOVE_DASHBOARD_SPACE
      }),
      addNewPanel (spaceId) {
        this.wizard.active = true
        this.wizard.space = spaceId
      },
      finishNewPanel() {
        this.wizard.active = false
      },
      addNewSpace () {
        this.saveSpace(this.newSpaceName).then(spaceId => {
          this.$nextTick(() => {
            this.$refs.tabs.renameTabById(spaceId)
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