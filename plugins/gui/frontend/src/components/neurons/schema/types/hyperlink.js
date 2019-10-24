import {entities} from '../../../../constants/entities'

import {mapState, mapMutations} from 'vuex'
import {UPDATE_DATA_VIEW} from "../../../../store/mutations";

export default {
    computed: {
        ...mapState({
            entityToState(state) {
                return entities.map(entity => entity.name).reduce((entityToState, entityName) => {
                    entityToState[entityName] = state[entityName]
                    return entityToState
                }, {})
            }
        }),
        hyperlink() {
            if (this.schema.link){
                return { href: this.schema.link || '#'}
            }
            if (!this.schema.path || !this.schema.path.length || !this.entityToState[this.schema.path[0]]) return null
            let hyperlinks = this.entityToState[this.schema.path[0]].hyperlinks.data
            if (!hyperlinks) return null
            let evalResult = eval(hyperlinks[this.schema.path[1]])
            if (!evalResult) return null

            let qualifiedPath = this.schema.path.slice(3).filter(x => typeof(x) === 'string').join('.')
            if (!evalResult[qualifiedPath]) return null

            let linkData = evalResult[qualifiedPath](this.processedData)
            return { ...linkData, href: linkData.href || '#'}
        },
        hyperlinkHref() {
            if (!this.hyperlink) return undefined
            return this.hyperlink.href
        }
    },
    methods: {
        ...mapMutations({
            updateView: UPDATE_DATA_VIEW
        }),
        onClickLink() {
            if (!this.hyperlink) return true
            if (this.hyperlink.type === 'link') return true
            if (this.hyperlink.type !== 'query') return false

            this.updateView({
                module: this.hyperlink.module, view: {
                    page: 0, query: {
                        filter: this.hyperlink.filter, expressions: []
                    }
                }
            })
            this.$router.push({
                path: '/' + this.hyperlink.module
            })
        }
    }
}