<template>
  <div class="x-card">
    <div class="header">
      <x-button
        v-if="reversible"
        link
        class="back"
        @click="$emit('back')"
      >&lt;</x-button>
      <x-title
        v-if="logo"
        :logo="logo"
      >{{ title }}</x-title>
      <div
        v-else
        class="title"
        :title="title"
      >{{ title }}</div>
      <div class="actions">
        <x-button
          v-if="editable"
          class="edit"
          title="Edit"
          link
          @click="$emit('edit')"
        ><md-icon>edit</md-icon></x-button>
        <x-button
          v-if="removable"
          class="remove"
          title="Remove"
          link
          @click="$emit('remove')"
        ><md-icon>clear</md-icon></x-button>
      </div>
    </div>
    <div class="body">
      <slot />
    </div>
  </div>
</template>

<script>
  import xTitle from './Title.vue'
  import xButton from '../inputs/Button.vue'

  export default {
    name: 'XCard',
    components: {
      xTitle, xButton
    },
    props: {
      title: {
        type: String,
        required: true
      },
      logo: {
        type: String,
        default: ''
      },
      editable: {
        type: Boolean,
        default: false
      },
      removable: {
        type: Boolean,
        default: false
      },
      reversible: {
        type: Boolean,
        default: false
      }
    }
  }
</script>

<style lang="scss">
    .x-card {
        display: flex;
        flex-direction: column;
        background-color: white;
        box-shadow: 0 2px 12px 0px rgba(0, 0, 0, 0.2);
        border-radius: 2px;

        > .header {
            display: flex;
            width: 100%;
            padding: 12px;

          .back {
                font-size: 24px;
            }

            > .x-title {
                width: calc(100% - 36px);

                .md-image {
                    height: 48px;
                }

                .text {
                    font-size: 24px;
                    margin-left: 24px;
                    text-overflow: ellipsis;
                    width: calc(100% - 84px);
                    overflow-x: hidden;
                    line-height: 48px;
                }
            }

            > .title {
                font-size: 16px;
                flex: 1 0 auto;
                text-overflow: ellipsis;
                white-space: nowrap;
                overflow: hidden;
            }

            .actions {
                display: flex;
                line-height: 20px;
                width: 48px;
                margin-left: 4px;

                .x-button {
                  height: 20px;
                  padding: 0;

                  .md-icon {
                    font-size: 20px !important;
                    height: 20px;
                    line-height: 20px;
                  }

                  &:hover {
                    cursor: pointer;
                    text-shadow: $text-shadow;
                  }
                }
            }
        }
        > .body {
          padding: 12px;
          height: calc(100% - 72px);
        }
    }
</style>