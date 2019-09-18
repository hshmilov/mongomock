<template>
  <div class="x-checkbox-list">
    <component
      :is="listWrapperType"
      v-model="orderedItems"
      ghost-class="ghost"
      class="list"
      :class="{ draggable }"
      @start="onStartDrag"
      @end="onEndDrag"
    >
      <div
        v-for="item in items"
        :key="item.name"
        :title="item.title"
        class="list__item"
        :class="{ dragging }"
      >
        <md-icon md-src="src/assets/icons/action/drag.svg"></md-icon>
        <x-checkbox
          :value="item.name"
          :label="item.title"
          :data="value"
          @change="onChangeCheckbox"
        >
          <slot :item="item" />
        </x-checkbox>

      </div>
    </component>
  </div>
</template>

<script>
  import draggable from 'vuedraggable'
  import xCheckbox from '../../axons/inputs/Checkbox.vue'

  export default {
    name: 'XCheckboxList',
    components: {
      draggable, xCheckbox
    },
    props: {
      items: {
        type: Array,
        required: true
      },
      value: {
        type: Array,
        default: () => []
      },
      draggable: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        dragging: false
      }
    },
    computed: {
      listWrapperType () {
        return this.draggable? 'draggable' : 'div'
      },
      orderedItems: {
        get () {
          return this.items
        },
        set (newItems) {
          this.$emit('change', newItems)
        }
      },
      itemNames () {
        return this.orderedItems.map(item => item.name)
      }
    },
    methods: {
      onChangeCheckbox (checked) {
        const hiddenChecked = checked.filter(itemName => !this.itemNames.includes(itemName))
        const visibleOrderedChecked = this.itemNames.filter(itemName => checked.includes(itemName))
        this.$emit('input', [...hiddenChecked, ...visibleOrderedChecked])
      },
      onStartDrag () {
        this.dragging = true
      },
      onEndDrag () {
        this.dragging = false
      }
    }
  }
</script>

<style lang="scss">
    .x-checkbox-list {
        margin-top: 8px;
        overflow: auto;
        height: 360px;

        .list {
            display: grid;
            grid-template-columns: 1fr 1fr;
            font-size: 12px;
            color: $theme-black;

            &__item {
                background: $theme-white;
                display: flex;
                padding-right: 16px;

                .md-icon {
                  visibility: hidden;
                    font-size: 24px !important;
                    fill: $grey-3;
                    min-width: 16px;
                    width: 16px;
                    margin: 0 -8px 0 -4px;
                }


                .x-checkbox {
                    margin-left: -4px;
                }
            }

            &.draggable {
              .list__item:not(.dragging):hover {
                border: 1px solid $grey-2;

                .md-icon {
                  visibility: visible;
                }
              }

              .ghost {
                  border: 1px solid rgba($theme-blue, 0.4);
              }
            }

        }
    }
</style>