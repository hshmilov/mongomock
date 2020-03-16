<template>
  <div class="x-milestone">
    <span
      v-if="interactive"
      class="x-milestone-status"
    >
      <MdIcon
        v-if="completed"
        class="x-milestone-status--completed"
        style="color: #0FBC18;"
      >check_circle</MdIcon>
      <MdIcon
        v-else
        style="color: #efefef;"
      >radio_button_unchecked</MdIcon>
    </span>
    <div class="x-miestone_container">
      <section class="x-milestone_header">
        <h5 class="x-milestone_header_title">
          {{ title }}
        </h5>
        <div class="x-milestone_header_actions">
          <span
            v-if="description"
            class="x-milestone_expand"
            @click="toggleExpantionPanel"
          >
            <MdIcon v-if="expand">keyboard_arrow_up</MdIcon>
            <MdIcon v-else>keyboard_arrow_down</MdIcon>
          </span>
          <XButton
            v-if="interactive"
            tabindex="-1"
            class="x-milestone_action"
            :disabled="completed"
            @click="goToMilestoneRelatedPage"
          >{{ buttonText }}</XButton>
        </div>
      </section>
      <XTransitionExpand>
        <div v-if="expand">
          <p class="x-milestone_content">
            {{ description }}
          </p>
          <XButton
            v-if="link"
            tabindex="-1"
            link
            @click="goToDocsPage"
          >
            Learn more
          </XButton>
        </div>
      </XTransitionExpand>
    </div>
  </div>
</template>

<script>
import XButton from '../../axons/inputs/Button.vue';
import { GettingStartedPubSub } from '../../App.vue';
import XTransitionExpand from '../../transitions/TransitionExpand.vue';

export default {
  components: { XButton, XTransitionExpand },
  props: {
    completed: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      required: true,
    },
    description: {
      type: String,
    },
    link: {
      type: String,
    },
    path: {
      type: String,
      required: true,
    },
    interactive: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      expand: false,
    };
  },
  computed: {
    buttonText() {
      return this.completed ? 'Completed' : 'Let\'s Do It';
    },
  },
  methods: {
    goToDocsPage() {
      window.open(this.link, '_blank');
    },
    toggleExpantionPanel() {
      this.expand = !this.expand;
    },
    goToMilestoneRelatedPage() {
      // redirect in the platform to the designated page for this milestone
      GettingStartedPubSub.$emit('getting-started-open-state');
      this.$router.push({ path: this.path });
    },
  },
};
</script>

<style lang="scss" scoped>
    .x-milestone {
        width: 100%;
        display: flex;
        flex-direction: row;
        align-content: flex-start;
        position: relative;
        padding: 10px 0;

        &::after {
            background-color: #efefef;
            bottom: -5px;
            content: '';
            display: block;
            height: 2px;
            left: 50%;
            position: absolute;
            transform: translate(-50%,0);
            width: 96%;
        }

        .x-milestone-status {
            position: relative;
            top: 8px;
        }
        .x-miestone_container {
            flex-grow: 1;
        }
        .x-milestone_header {
            padding: 0 10px;
            display: flex;
            flex-direction: row;
            height: 40px;
            justify-content: space-between;
            align-content: center;
            align-items: center;
            .x-milestone_header_title {
                margin: 0;
                font-size: 14px;
            }
            .x-milestone_header_actions {
                display: flex;
                justify-content: center;
                align-content: center;
            }
            .x-milestone_action {
                width: 90px;
            }
            .x-milestone_expand {
                cursor: pointer;
            }
        }

        .x-milestone_content {
            padding: 0 10px;
            word-wrap: break-word;
            max-width: 100%;
            white-space: pre-line;
            font-weight: 300;
        }
    }
</style>
