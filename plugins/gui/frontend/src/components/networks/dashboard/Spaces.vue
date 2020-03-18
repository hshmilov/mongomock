<template>
  <div class="x-spaces">
    <XRoleGateway
      permission-type="Dashboard"
      permission-level="ReadWrite"
    >
      <template slot-scope="{ allowed }">
        <XTabs
          v-if="spaces.length"
          ref="tabs"
          :extendable="allowed"
          remove-text="Remove Space"
          @add="addNewSpace"
          @rename="renameSpace"
          @remove="removeSpace"
          @click="selectSpace"
        >
          <XTab
            :id="defaultSpace.uuid"
            :title="defaultSpace.name"
            :selected="currentSpace === defaultSpace.uuid"
            :editable="allowed"
          >
            <XDefaultSpace
              v-if="active"
              slot-scope="{ active }"
              :panels="defaultSpace.panels"
              :panels-order="defaultSpace.panels_order"
              @add="() => addNewPanel(defaultSpace.uuid)"
              @edit="editPanel"
            />
          </XTab>
          <XTab
            v-if="allowed"
            :id="personalSpace.uuid"
            :title="personalSpace.name"
            :selected="currentSpace === personalSpace.uuid"
          >
            <XPanels
              v-if="active"
              slot-scope="{ active }"
              :panels="personalSpace.panels"
              :panels-order="personalSpace.panels_order"
              @add="() => addNewPanel(personalSpace.uuid)"
              @edit="editPanel"
            />
          </XTab>
          <XTab
            v-for="space in customSpaces"
            :id="space.uuid"
            :key="space.uuid"
            :title="space.name"
            :selected="currentSpace === space.uuid"
            :editable="allowed"
            :removable="allowed"
          >
            <XPanels
              v-if="active"
              slot-scope="{ active }"
              :panels="space.panels"
              :panels-order="space.panels_order"
              @add="() => addNewPanel(space.uuid, true)"
              @edit="editPanel"
            />
          </XTab>
          <div slot="remove_confirm">
            <div>This space will be completely removed from the system and</div>
            <div>no other user will be able to use it.</div>
            <div>Removing the space is an irreversible action.</div>
          </div>
        </XTabs>
      </template>
    </XRoleGateway>
    <XWizard
      v-if="wizard.active"
      :space="wizard.space"
      :panel="wizard.panel"
      @close="closeWizard"
    />
  </div>
</template>

<script>
import { mapState, mapMutations, mapActions } from 'vuex';
import XTabs from '../../axons/tabs/Tabs.vue';
import XTab from '../../axons/tabs/Tab.vue';
import XDefaultSpace from './DefaultSpace.vue';
import XPanels from './Panels.vue';
import XWizard from './Wizard.vue';

import {
  SAVE_DASHBOARD_SPACE, CHANGE_DASHBOARD_SPACE, REMOVE_DASHBOARD_SPACE,
  SET_CURRENT_SPACE,
} from '../../../store/modules/dashboard';

export default {
  name: 'XSpaces',
  components: {
    XTabs, XTab, XDefaultSpace, XPanels, XWizard,
  },
  props: {
    spaces: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      wizard: {
        active: false,
        space: '',
      },
      processing: false,
      editCustomSpace: false,
    };
  },
  computed: {
    ...mapState({
      currentSpace(state) {
        return state.dashboard.currentSpace || this.defaultSpace.uuid;
      },
    }),
    defaultSpace() {
      return this.spaces.find((space) => space.type === 'default');
    },
    personalSpace() {
      return this.spaces.find((space) => space.type === 'personal');
    },
    customSpaces() {
      return this.spaces.filter((space) => space.type === 'custom');
    },
    newSpaceName() {
      for (let i = this.customSpaces.length - 1; i >= 0; i--) {
        const matches = this.customSpaces[i].name.match('Space (\\d+)');
        if (matches && matches.length > 1) {
          return `Space ${parseInt(matches[1]) + 1}`;
        }
      }
      return 'Space 1';
    },
  },
  methods: {
    ...mapMutations({
      selectSpace: SET_CURRENT_SPACE,
    }),
    ...mapActions({
      saveSpace: SAVE_DASHBOARD_SPACE,
      renameSpace: CHANGE_DASHBOARD_SPACE,
      removeSpace: REMOVE_DASHBOARD_SPACE,
    }),
    addNewPanel(spaceId, isCustomSpace) {
      this.editCustomSpace = isCustomSpace;
      this.wizard.active = true;
      this.wizard.space = spaceId;
    },
    closeWizard() {
      this.wizard.active = false;
      this.wizard.space = '';
      this.wizard.panel = null;
      this.editCustomSpace = false;
    },
    editPanel(panel) {
      this.wizard.active = true;
      this.wizard.panel = { ...panel };
      this.wizard.space = this.currentSpace;
    },
    addNewSpace() {
      if (this.processing) return;
      this.processing = true;
      this.saveSpace(this.newSpaceName).then((spaceId) => {
        this.$nextTick(() => {
          this.$refs.tabs.renameTabById(spaceId);
          this.$refs.tabs.selectTab(spaceId);
          this.processing = false;
        });
      });
    },
  },
};
</script>

<style lang="scss">
    .x-spaces {
        height: calc(100% - 42px);
    }
</style>
