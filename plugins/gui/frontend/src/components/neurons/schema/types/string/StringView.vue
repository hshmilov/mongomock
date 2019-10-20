<template>
  <img
    v-if="schema.format && schema.format === 'image'"
    :src="value"
    height="24"
    :style="{borderRadius: '50%'}"
    class="md-image"
  >
  <img
    v-else-if="schema.format && schema.format === 'logo'"
    :src="require(`Logos/adapters/${value}.png`)"
    :alt="value"
    height="24"
    class="logo md-image"
  >
  <svg-icon
    v-else-if="schema.format && schema.format === 'icon'"
    :name="`symbol/${value}`"
    :original="true"
    height="16"
  />
  <div
    v-else-if="hyperlink"
  >
    <a
      :href="hyperlinkHref"
      @click="onClickLink(hyperlink)"
    >{{ processedData }}
    </a>
  </div>
  <md-chip
    v-else-if="schema.format && schema.format === 'tag'"
    class="tag"
  >{{ processedData }}</md-chip>
  <div v-else-if="processedData">{{ processedData }}</div>
  <div v-else>&nbsp;</div>
</template>

<script>
  import hyperlinkMixin from '../hyperlink.js'
  import { formatDate } from '../../../../../constants/utils'

  export default {
    name: 'XStringView',
    mixins: [hyperlinkMixin],
    props: {
      schema: {
        type: Object,
        required: true
      },
      value: {
        type: [String, Array],
        default: ""
      },
      link: {
          type: String,
          default: ''
      }
    },
    data () {
        return {
          inHover: false,
          position: {
            top: false,
            left: false
          }
        }
      },
    computed: {
      processedData() {
        return this.format(this.value)
      },
      fieldName() {
        return this.schema.title || "";
      },
      logo() {
        if (this.schema.name && this.schema.name.indexOf('adapters_data') > -1) {
          return this.schema.name.match(/adapters_data.(.*?)\.+/i)[1];
        }
        return false;
      }
    },
    methods: {
      format(value) {
        if (!this.schema.format) return value;
        if (
          this.schema.format.includes("date") ||
          this.schema.format.includes("time")
        ) {
          if (!value) return "";
          return formatDate(value, this.schema);
        }
        if (this.schema.format === "password") {
          return "********";
        }
        return value;
      },
      onHover () {
        this.inHover = true;
        this.$nextTick(() => {
        let boundingBox = this.$refs.xtooltip.$el.getBoundingClientRect()
        this.position = {
          top: this.position.top || Boolean(boundingBox.bottom > window.innerHeight - 80),
          left: this.position.left || Boolean(boundingBox.right > window.innerWidth - 24)
        }
      })
      },
      onLeave (event) {
        this.inHover = false;
      }
    }
  };
</script>

<style lang="scss">

.item-title,
.field-name {
  text-align: start;
}

.md-chip{
  &.not-tag {
      border: 1px solid rgba($theme-orange, 0.2)!important;
      background-color: transparent!important;
      height: 20px;
      line-height: 20px;
    }
}
  .x-tooltip.enforce {
    position: absolute;
  }
</style>