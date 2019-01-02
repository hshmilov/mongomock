import {mapState, mapMutations} from 'vuex'
import {UPDATE_DATA_VIEW} from "../../store/mutations";

export default {
    computed: {
        ...mapState({
            state(state) {
                return state
            }
        }),
        hyperlink() {
            if (!this.state || !this.schema.path) return null
            let hyperlinks = this.state[this.schema.path[0]].hyperlinks.data
            if (!hyperlinks) return null
            let data = eval(hyperlinks[this.schema.path[1]])
            if (!data) return null

            let qualified_path = this.schema.path.slice(3).filter(x => typeof(x) === 'string').join('.')
            data = data[qualified_path]
            if (!data) return null

            let linkData = data(this.processedData)
            linkData.href = linkData.href || '#'
            return linkData
        },
    },
    watch: {
        value(newValue, oldValue) {
            if (newValue !== oldValue) {
                this.data = newValue
            }
            if (newValue) {
                this.validate()
            }
        }
    },
    methods: {
        ...mapMutations({
            updateView: UPDATE_DATA_VIEW
        }),
        valueClicked(hyperlink) {
            if (!hyperlink) return true
            if (hyperlink.type == 'link') return true
            if (hyperlink.type != 'query') {
                console.error('Unknown data type ' + hyperlink.type)
                return false
            }
            let module = hyperlink.module
            let filter = hyperlink.filter
            this.updateView({
                module, view: {
                    page: 0, query: {filter, expressions: []}
                }
            })
            this.$router.push({path: '/' + module})
        }
    }
}