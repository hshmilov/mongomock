<template>
  <a
    :href="href"
    @click="onClick"
  >
    <slot />
  </a>
</template>

<script>

  import {mapMutations} from 'vuex'
  import {UPDATE_DATA_VIEW} from '../../../store/mutations'

  export default {
    name: 'XHyperlink',
    props: {
      type: {
        type: String,
        required: true
      },
      href: {
        type: String,
        default: undefined
      },
      module: {
        type: String,
        default: ''
      },
      filter: {
        type: String,
        default: ''
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      onClick() {
        if (this.type === 'link') return true
        if (this.type !== 'query') return false

        this.updateView({
          module: this.module,
          view: {
            page: 0, query: {
              filter: this.filter, expressions: []
            }
          }
        })
        this.$router.push({
          path: '/' + this.module
        })
      }
    }
  }
</script>

<style lang="scss">

</style>