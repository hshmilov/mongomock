<template>
  <md-drawer :md-active.sync="open" md-swipeable class="md-right x-getting-started">
    <header class="x-getting-started_header">
      <h1>Getting Started With Axonius</h1>
      <x-progress-gauge :steps="steps" :progress="progress" />
    </header>
    <md-list class="md-scrollbar x-getting-started_content">
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
        <x-checkbox v-model="shouldAutoOpen" @change="settingChanged" label="Show this checklist on login"></x-checkbox>
      </h4>
    </footer>
  </md-drawer>
</template>

<script>

import XMilestone from './Milestone'
import XProgressGauge from '../../axons/visuals/ProgressGauge'
import XCheckbox from "../../axons/inputs/Checkbox.vue";
import json from './getting-started.mock.json'

function getCompletedMilestones(item) {
    return item.completed
}

export default {
    components: { XMilestone, XProgressGauge, XCheckbox },
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
        }
    }
}
</script>

<style lang="scss" scoped>
.x-getting-started {
    position: absolute;
    height: 100vh;
    header, footer {
        display: flex;
        padding: 10px 20px;
    }

    footer {
        height: 60px;
    }

    .x-getting-started_header {
        justify-content: space-around;
        align-items: center;
        height: 100px;
        h1 {
            font-size: 20px;
        }
        &::after {
        background-color: #ea9f2a;
        top: 100px;
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
    .x-getting-started_content {
        height: calc(100% - 160px);
        overflow-y: scroll;
    }
}
.md-drawer {
    width: 450px;
    max-width: 450px;
  }

  .md-content {
    padding: 16px;
  }

</style>
