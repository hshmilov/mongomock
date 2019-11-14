import Vue from 'vue'
import xSelect from './Select.vue';
import { FETCH_DATA_LABELS } from '../../../store/actions'
import {mapActions, mapGetters, mapState} from 'vuex';
import {IS_ENTITY_RESTRICTED} from '../../../store/modules/auth';
import uniqBy from 'lodash/uniqBy'

const withDynamicData = (component, params) => {
    const inheritedProps = {...xSelect.props};

    return Vue.component('withDynamicData', {
        props:{
            ...inheritedProps,
            schema: {
                type: Object,
                default: () => {}
            }
        },
        computed: {
        ...mapState({
                [`${params.attributeName}`] (state) {
                    // if one of the sources are not in state, fetch all by return false
                    const modules = this.usedModules
                    if (modules.every( name => state[name][params.attributeName].data ) ) {
                        return uniqBy(modules.reduce((acc, item) => {
                                acc.push(...state[item][params.attributeName].data)
                                return acc
                            }, []), 'name'
                            ).sort()
                    }
                    return false
                }
            }),
        ...mapGetters({
                isEntityRestricted: IS_ENTITY_RESTRICTED
            }),
            usedModules() {
                return params.moduleName.filter( moduleName => !this.isEntityRestricted(moduleName))
            },
        },
        created() {
            if(!this[params.attributeName]) {
                this.usedModules.map( name => {
                    this.fetchData({ module: name })
                })
            }
        },
        methods: {
            ...mapActions({
                fetchData: params.action
            })
        },
        render(createElement) {
            const passedProps = this.$props
            const options = this[params.attributeName] || []

            return createElement(component, {
                props: {
                    ...passedProps,
                    options,
                    missingItemsLabel: params.missingItemsLabel,
                    placeholder: this.$props.schema.title,
                    searchPlaceholder: this.$props.schema.title,
                    allowCustomOption: this.$props.schema.source.options['allow-custom-option']
                },
                on: {
                    ...this.$listeners
                }
            })
        }
    })
}



export const xTagSelect = withDynamicData(xSelect,{
    id:'tagSelect',
    action: FETCH_DATA_LABELS,
    moduleName: ['devices','users'],
    attributeName: 'labels',
    missingItemsLabel: ''
})