<template>
  <md-drawer :md-active.sync="open" md-swipeable class="md-right x-getting-started">
    <header class="x-getting-started_header">
      <h1>Getting Started With Axonius</h1>
      <x-progress-gauge :steps="steps" :progress="progress" />
    </header>
    <header v-if="completed" class="x-getting-started_completion">
      <md-icon class="completion_icon">emoji_events</md-icon>
      <div class="completion_info">
        <h4>Congratulations!</h4><br/>
        <span>You have completed all the "Getting Started With Axonius" milestones.</span><br/>
        <span>
          Use the
          <router-link to="/settings#global-settings-tab">Global Settings</router-link> to hide/display the "Getting Started With Axonius" checklist.
        </span>
      </div>
    </header>
    <md-list class="md-scrollbar x-getting-started_content" :class="{ completed }">
      <md-list-item v-for="item in items" :key="item.id">
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
    <footer>
      <h4>
        <x-checkbox
          v-model="shouldAutoOpen"
          @change="settingChanged"
          label="Show this checklist on login"
        ></x-checkbox>
      </h4>
    </footer>
  </md-drawer>
</template>

<script>

import XMilestone from './Milestone'
import XButton from '../../axons/inputs/Button'
import XProgressGauge from '../../axons/visuals/ProgressGauge'
import XCheckbox from "../../axons/inputs/Checkbox.vue";
import json from './getting-started.mock.json'

function getCompletedMilestones(item) {
    return item.completed
}

export default {
    components: { XMilestone, XProgressGauge, XCheckbox, XButton },
    props: {
        items: {
            type: Array,
            default: () => json.data
        },
        open: {
            type: Boolean,
            default: true,
        },
        settings: {
            type: Object,
            default: () => ({
                autoOpen: true,
                interatcive: true,
            })
        }
    },
    methods: {
        settingChanged(value) {
            this.$emit('settingChanged', value)
        }
    },
    data() {
        return {
            shouldAutoOpen: this.settings.autoOpen
        }
    },
    computed: {
        steps() {
            return this.items.length
        },
        progress() {
            return this.items.filter(getCompletedMilestones).length
        },
        completed() {
            return this.progress == this.steps
        }
    }
}
</script>

<style lang="scss" scoped>

$header_section: 100px;
$completion_section: 125px;
$footer_section: 60px;

@mixin fixed_section {
    justify-content: space-around;
    align-items: center;
    height: $header_section;
    &::after{
        background-color: #ea9f2a;
        top: $header_section;
        content: '';
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
    header, footer {
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

        .completion_icon {
            margin: 0;
            color: #ea9f2a;
            font-size: 20px;
        }

        .completion_info{
            padding: 0 10px;
            h4 {
                margin: 0;
            }
        }

        &::after{
            top: $completion_section + $header_section;
        }
    }

    .x-getting-started_header {
        @include fixed_section();
        h1 {
            font-size: 20px;
        }
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
