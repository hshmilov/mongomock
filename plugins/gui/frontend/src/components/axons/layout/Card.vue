<template>
  <div
    class="x-card"
    :class="{'transparent-box': transparent}"
  >
    <div class="header">
      <div class="header__title">
        <XButton
          v-if="reversible"
          type="link"
          class="back-button"
          @click="$emit('back')"
        >{{ backTitle }}</XButton>
        <XTitle
          v-if="title"
          :logo="logo"
        >{{ title }} </XTitle>
      </div>
    </div>
    <div class="body">
      <slot />
    </div>
  </div>
</template>

<script>
import XTitle from './Title.vue';
import XButton from '../inputs/Button.vue';

export default {
  name: 'XCard',
  components: {
    XTitle,
    XButton,
  },
  props: {
    title: {
      type: String,
      default: '',
    },
    backTitle: {
      type: String,
      default: '',
    },
    logo: {
      type: String,
      default: '',
    },
    reversible: {
      type: Boolean,
      default: false,
    },
    transparent: {
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

    &.transparent-box {
      box-shadow: initial;
      > .body, .header {
        padding: 12px 0 12px 0;
      }
    }

    .header {
      display: flex;
      padding: 12px;

      > .header__title {
        display: flex;
        flex: 1;
        overflow: hidden;

        > .back-button {
          padding-left: 0;
          border-left: 0;
          margin-right: 6px;
          font-size: 18px;
          font-weight: inherit;
          line-height: 36px;
          flex: none;
          color: $theme-orange;
            &:after {
                right: 2px;
                @include triangle('right', 4px, $color: $theme-orange);
                margin: 0;
            }
            &:hover {
                > span {
                    text-decoration: underline;
                }
            }
        }

        > .x-title {
          width: calc(100% - 36px);

          .md-image {
            height: 36px;
          }

          .text {
            font-size: 18px;
            text-overflow: ellipsis;
            width: calc(100% - 84px);
            overflow-x: hidden;
            line-height: 36px;
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

    > .body {
      padding: 12px;
      height: calc(100% - 72px);
    }

  }
</style>
