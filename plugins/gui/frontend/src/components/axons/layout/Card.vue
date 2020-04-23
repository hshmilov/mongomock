<template>
  <div class="x-card">
    <div class="header">
      <div class="header__title">
        <XButton
          v-if="reversible"
          type="link"
          class="back"
          @click="$emit('back')"
        >&lt;</XButton>
        <XTitle
          v-if="logo"
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
    reversible: {
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

        > .body {
          padding: 12px;
          height: calc(100% - 72px);
        }

    }
</style>
