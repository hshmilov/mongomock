<template>
  <div :class="{'x-card': true, 'custom-card': draggable}">
    <div class="header">
      <div class="header__title">
        <XButton
          v-if="reversible"
          link
          class="back"
          @click="$emit('back')"
        >&lt;</XButton>
        <XTitle
          v-if="logo"
          :logo="logo"
        >{{ title }} </XTitle>
        <div
          v-else
          class="card-title"
          :title="title"
        >{{ title }}</div>
      </div>
      <div class="actions">
        <span
          v-if="isChartFilterable"
          class="actions__search"
          @click="$emit('toggleShowSearch')"
        >
          <VIcon
            size="15"
            class="cardSearch-expression-handle"
          >$vuetify.icons.cardSearch</VIcon>
        </span>
        <ADropdown
          v-if="draggable"
          class="actions__menu"
          :trigger="['click']"
          placement="bottomRight"
        >
          <span
            class="ant-dropdown-link card_menu"
            href="#"
          >
            <VIcon
              size="15"
              class="verticaldots-expression-handle"
            >$vuetify.icons.verticaldots</VIcon>
          </span>
          <AMenu slot="overlay">
            <AMenuItem
              v-if="editable"
              id="edit_chart"
              key="0"
              @click="$emit('edit')"
            >
              Edit Chart
            </AMenuItem>
            <AMenuItem
              v-if="removable"
              id="remove_chart"
              key="1"
              @click="$emit('remove')"
            >
              Remove Chart
            </AMenuItem>
            <AMenuItem
              v-if="exportable"
              id="export_chart"
              key="2"
              @click="$emit('export')"
            >
              Export to CSV
            </AMenuItem>
            <AMenuItem
              id="move_or_copy_chart"
              key="3"
              @click="$emit('moveOrCopy')"
            >
              Move or Copy
            </AMenuItem>
            <AMenuItem
              id="refresh_chart"
              key="4"
              @click="$emit('refresh')"
            >
              Refresh
            </AMenuItem>
          </AMenu>
        </ADropdown>
      </div>
    </div>
    <div class="body">
      <slot />
    </div>
    <div>
      <span
        v-if="draggable"
        class="drag_handler"
      >
        <VIcon
          size="15"
          class="cardDraggable-expression-handle"
        >$vuetify.icons.cardDraggable</VIcon>
      </span></div>
  </div>
</template>

<script>
import XTitle from './Title.vue';
import XButton from '../inputs/Button.vue';

export default {
  name: 'XCard',
  components: {
    XTitle, XButton,
  },
  props: {
    title: {
      type: String,
      default: '',
    },
    logo: {
      type: String,
      default: '',
    },
    editable: {
      type: Boolean,
      default: false,
    },
    removable: {
      type: Boolean,
      default: false,
    },
    exportable: {
      type: Boolean,
      default: false,
    },
    reversible: {
      type: Boolean,
      default: false,
    },
    draggable: {
      type: Boolean,
      default: false,
    },
    showMenu: {
      type: Boolean,
      default: false,
    },
    isChartFilterable: {
      type: Boolean,
      default: false,
    },
  },
};
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
            > .header__title .card-title {

                .md-icon {
                  visibility: hidden;
                  font-size: 24px !important;
                  fill: $grey-3;
                  min-width: 16px;
                  width: 16px;
                  margin: 0 12px 0 -4px;
                }
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
                  font-weight: normal;
              }
          }

        }

        .actions {
          .actions__menu {
            cursor: pointer;
            padding: 8px 0;
          }

          .actions__search {
            cursor: pointer;
            margin-right: 8px;
          }
        }

        > .body {
          padding: 12px;
          height: calc(100% - 72px);
        }

        .drag_handler {
          width: 35px;
          margin: 0 auto;
          display: block;
          padding: 0 5px;
          :hover {
            cursor: move;
          }
        }

    }
</style>
