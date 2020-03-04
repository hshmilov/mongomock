<template>
  <div class="x-card">
    <div class="header">
      <div class="header__title">
        <x-button
          v-if="reversible"
          link
          class="back"
          @click="$emit('back')"
        >&lt;</x-button>
        <x-title
          v-if="logo"
          :logo="logo"
        >{{ title }} </x-title>
        <div
          v-else
          class="card-title"
          :title="title"
        ><md-icon v-if="draggable"
            md-src="src/assets/icons/action/drag.svg"></md-icon>{{ title }}</div>
      </div>
      <div class="actions">
        <x-button
          v-if="exportable"
          class="export"
          title="Export to CSV"
          link
          @click="$emit('export')"
        ><md-icon md-src="src/assets/icons/action/export.svg"></md-icon></x-button>
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
        default: true
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
      exportable: {
        type: Boolean,
        default: false
      },
      reversible: {
        type: Boolean,
        default: false
      },
      draggable: {
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
        border: 2px solid transparent;

        &.card__item .header {
            border: 1px solid transparent;
            > .header__title .card-title {
                display: flex;

                .md-icon {
                  visibility: hidden;
                  font-size: 24px !important;
                  fill: $grey-3;
                  min-width: 16px;
                  width: 16px;
                  margin: 0 12px 0 -4px;
                }
            }
            &:hover {
              cursor: move;
              border: 1px solid #DEDEDE;
            }
          }

        .header {
          display: flex;
          padding: 12px;

            > .header__title {
              display: flex;
              flex: 1;
              overflow: hidden;

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

              > .card-title {
                  font-size: 16px;
                  flex: 1 0 auto;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                  overflow: hidden;
                  max-width: 100%;
              }
          }
          .actions {
            display: flex;
            align-items: center;
            .x-button {
              height: 20px;
              padding: 0;

              &.export .md-icon{
                height: 18px;
                line-height: 17px
              }

              .md-icon {
                font-size: 20px !important;
                height: 20px;
                line-height: 20px;
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