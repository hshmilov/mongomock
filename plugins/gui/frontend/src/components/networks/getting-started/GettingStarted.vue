<template>
  <md-drawer :md-active.sync="open" md-swipeable class="md-right x-getting-started">
    <header
      v-bind:class="{'x-getting-started_header': true, 'not-interactive': !settings.interactive}"
    >
      <h1>Getting Started With Axonius</h1>
      <x-progress-gauge v-if="settings.interactive" :steps="steps" :progress="progress" />
    </header>
    <header v-if="completed && settings.interactive" class="x-getting-started_completion">
      <span>
          <svg-icon class="completion_icon" :name="`symbol/troffy`" :original="true" height="20px"></svg-icon>
      </span>
      <div class="completion_info">
        <h4>Congratulations!</h4>
        <br />
        <span>You have completed all the "Getting Started with Axonius" milestones.</span>
        <br />
        <span>
          Use the
          <router-link to="/settings#global-settings-tab">Global Settings </router-link>to hide/display the "Getting Started with Axonius" checklist.
        </span>
      </div>
    </header>
    <div class="x-getting-started_content" :class="{ completed }">
      <md-list class="md-scrollbar">
        <md-list-item v-for="item in milestones" :key="item.id">
          <x-milestone
            :completed="item.completed"
            :title="item.title"
            :description="item.description"
            :link="item.link"
            :path="item.path"
            :interactive="settings.interactive"
          />
        </md-list-item>
      </md-list>
    </div>
    <footer>
      <x-checkbox
        v-model="settings.autoOpen"
        @change="settingChanged"
        label="Show this checklist on login"
      ></x-checkbox>
    </footer>
  </md-drawer>
</template>

<script>
import XMilestone from "./Milestone.vue";
import XButton from "../../axons/inputs/Button.vue";
import XProgressGauge from "../../axons/visuals/ProgressGauge.vue";
import XCheckbox from "../../axons/inputs/Checkbox.vue";
import _get from "lodash/get";

import { mapState, mapActions } from "vuex";
import {
  GET_GETTING_STARTED_DATA,
  UPDATE_GETTING_STARTED_SETTINGS
} from "../../../store/modules/onboarding";

function getCompletedMilestones(item) {
  return item.completed;
}

export default {
  components: { XMilestone, XProgressGauge, XCheckbox, XButton },
  props: {
    value: {
      type: Boolean,
      default: false
    }
  },
  model: {
    prop: "value",
    event: "closed"
  },
  methods: {
    ...mapActions({
      fetchGettingStartedData: GET_GETTING_STARTED_DATA,
      updateGettingStartedSettings: UPDATE_GETTING_STARTED_SETTINGS
    }),
    settingChanged(value) {
      this.updateGettingStartedSettings({ autoOpen: value });
    }
  },
  computed: {
    ...mapState({
      settings: state => {
        return _get(state, "onboarding.gettingStarted.data.settings", {});
      },
      milestones: state => {
        return _get(state, "onboarding.gettingStarted.data.milestones", []);
      },
      loading: state => state.onboarding.gettingStarted.loading
    }),
    open: {
      get: function() {
        if (this.value) {
          // fetch most updated data every time the panel is opened.
          this.fetchGettingStartedData();
        }
        return this.value;
      },
      set: function(isOpen) {
        if (!isOpen) {
          this.$emit("closed");
        }
      }
    },
    steps() {
      return this.milestones.length;
    },
    progress() {
      return this.milestones.filter(getCompletedMilestones).length;
    },
    completed() {
      return this.progress == this.steps;
    }
  }
};
</script>

<style lang="scss" scoped>
$header_section: 100px;
$completion_section: 125px;
$footer_section: 60px;

@mixin fixed_section {
  justify-content: space-around;
  align-items: center;
  height: $header_section;
  &::after {
    background-color: #ea9f2a;
    top: $header_section;
    content: "";
    display: block;
    height: 1px;
    left: 50%;
    position: absolute;
    transform: translate(-50%, 0);
    width: 90%;
    z-index: 999;
  }
}

.x-getting-started {
  position: absolute;
  height: 100vh;
  header,
  footer {
    display: flex;
    padding: 10px 20px;
  }

  footer {
    height: $footer_section;
  }

  .x-getting-started_completion {
    @include fixed_section();
    height: $completion_section;
    flex-direction: row;
    align-items: flex-start;
    justify-content: flex-start;

    .completion_info {
      padding: 0 10px;
      h4 {
        margin: 0;
      }
    }

    &::after {
      top: $completion_section + $header_section;
    }
  }

  .x-getting-started_header {
    @include fixed_section();
    justify-content: space-between;
    h1 {
      font-size: 20px;
    }
  }
  .x-getting-started_header.not-interactive {
    justify-content: flex-start;
  }
  .x-getting-started_content {
    overflow-y: scroll;
    height: calc(100% - 160px);

    &.completed {
      height: calc(100% - 285px);
    }
  }
}
.md-drawer {
  width: 550px;
  max-width: 550px;
}

.md-content {
  padding: 16px;
}
</style>
