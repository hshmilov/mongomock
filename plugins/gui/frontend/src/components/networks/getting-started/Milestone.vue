<template>
  <div class="x-milestone">
    <span class="x-milestone-status">
      <i v-if="completed" class="material-icons" style="color: #0FBC18;">check_circle</i>
      <i v-else class="material-icons" style="color: #efefef;">radio_button_unchecked</i>
    </span>
    <div class="x-miestone_container">
      <section class="x-milestone_header">
        <h5 class="x-milestone_header_title">{{title}}</h5>
        <div class="x-milestone_header_actions">
          <span v-if="description" class="x-milestone_expand" @click="toggleExpantionPanel">
            <i v-if="expand" class="material-icons">keyboard_arrow_down</i>
            <i v-else class="material-icons">keyboard_arrow_up</i>
          </span>
          <x-button
            v-if="interactive"
            class="x-milestone_action"
            @click="goToDocsPage"
            :disabled="completed"
          >{{buttonText}}</x-button>
        </div>
      </section>
      <X-transition-expand>
        <div v-if="expand">
          <p class="x-milestone_content">{{description}}</p>
          <x-button v-if="link" @click="goToMilestoneRelatedPage" link>Learn More.</x-button>
        </div>
      </X-transition-expand>
    </div>
  </div>
</template>

<script>
import XButton from '../../axons/inputs/Button'
import XTransitionExpand from '../../transitions/TransitionExpand'

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
            required: true
        },
        interactive: {
            type: Boolean,
            default: true
        }
    }, 
    data() {
        return {
            expand: false
        }
    },
    computed: {
        buttonText() {
            return this.completed ? 'Completed' : `Let's Do It`
        }
    },
    methods: {
        goToDocsPage() {
            // redirect in the platform to the designated page for this milestone
        },
        toggleExpantionPanel() {
            this.expand = !this.expand
        },
        goToMilestoneRelatedPage() {
            // redirect to the docs
        }
    }
}
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
            width: 90%;
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
        }
    }
</style>