<template>
   <x-select class="x-language-picker" :options="languageList" v-model="language" placeholder="lang..."/>
</template>

<script>
    import xSelect from '../axons/inputs/Select.vue'
    import {mapState, mapMutations} from 'vuex'
    import {UPDATE_LANGUAGE} from '../../store/mutations'
    export default {
        name: "x-language-picker",
        components: {xSelect},
        computed: {
            ...mapState({
                languageList(state) {
                    if (state.auth.currentUser.data.oidc_data &&
                            state.auth.currentUser.data.oidc_data.claims &&
                            state.auth.currentUser.data.oidc_data.claims.optional_languages) {
                        return state.auth.currentUser.data.oidc_data.claims.optional_languages.map(lang => {
                            return {
                                name: lang, title: lang
                            }
                        })
                    }
                    return []
                },
                defaultLanguage(state) {
                    if (state.auth.currentUser.data.oidc_data &&
                            state.auth.currentUser.data.oidc_data.claims &&
                            state.auth.currentUser.data.oidc_data.claims.default_language) {
                        return state.auth.currentUser.data.oidc_data.claims.default_language
                    }
                    return ''
                },
                stateLanguage(state) {
                   if (state.interaction)
                      return state.interaction.language
                   return ''
                }
            }),
           language: {
              get() {
                 return this.stateLanguage || this.defaultLanguage || 'en'
              },
              set(value) {
                 this.updateLanguage(value)
              }
           }
        },
       methods: {
          ...mapMutations({
             updateLanguage: UPDATE_LANGUAGE
          })
       }

    }
</script>

<style lang="scss">
    .x-language-picker {
        img {
            width: 30px;
            margin-bottom: 8px;
            border-radius: 100%;
        }
       text-transform: uppercase;
    }
</style>