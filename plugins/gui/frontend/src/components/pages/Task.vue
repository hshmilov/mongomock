<template>
    <x-page class="x-task" :breadcrumbs="[
        { title: 'enforcements', path: { name: 'Enforcements'}},
    	{ title: 'tasks', path: {name: 'Tasks'} },
    	{ title: name }]" beta>
        <x-split-box>
            <template slot="main">
                <div class="header">
                    <x-array-view :schema="taskDetailsSchema" :value="taskData"/>
                </div>
                <div class="body">
                    <x-action v-bind="mainAction" read-only @click="selectActionMain"/>
                    <x-action-group v-for="item in successiveActions" v-bind="item" :key="item.condition"
                                    @select="selectAction"/>
                </div>
            </template>
            <x-card slot="details" v-if="currentActionName" v-bind="actionResCard">
                <x-action-result :data="actionInView.definition" :module="triggerView.entity" :view="triggerView.name"
                                 @click-one="runFilter"/>
            </x-card>
        </x-split-box>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xSplitBox from '../axons/layout/SplitBox.vue'
    import xCard from '../axons/layout/Card.vue'
    import xArrayView from '../neurons/schema/types/array/ArrayView.vue'
    import xAction from '../networks/enforcement/Action.vue'
    import xActionGroup from '../networks/enforcement/ActionGroup.vue'
    import xActionResult from '../networks/enforcement/ActionResult.vue'

    import {mapActions, mapMutations, mapState} from 'vuex'
    import {UPDATE_DATA_VIEW} from '../../store/mutations'
    import {FETCH_TASK} from '../../store/modules/tasks'

    import {
        actionsMeta,
        failCondition,
        mainCondition,
        postCondition,
        successCondition
    } from '../../constants/enforcement'

    export default {
        name: 'x-task',
        components: {
            xPage, xSplitBox, xCard, xArrayView,
            xAction, xActionGroup,
            xActionResult
        },
        computed: {
            ...mapState({
                triggerPeriods(state) {
                    if (!state.constants.constants || !state.constants.constants.trigger_periods) {
                        return []
                    }
                    return state.constants.constants.trigger_periods
                },
                taskData(state) {
                    let period = this.triggerPeriods.find((x) => {
                        return x[state.tasks.current.data.period] !== undefined
                    })
                    if (period) {
                        period = period[state.tasks.current.data.period]
                    }
                    return {
                        ...state.tasks.current.data,
                        period
                    }
                },
                ecFilter(state) {
                    if (!this.triggerView) return null
                    return state[this.triggerView.entity].view.ecFilter
                }
            }),
            id() {
                return this.$route.params.id
            },
            name() {
                if (!this.taskData || !this.taskData.enforcement) return ''

                return this.taskData.enforcement
            },
            taskDetailsSchema() {
                return {
                    type: 'array',
                    items: [{
                        name: 'started', title: 'Started', type: 'string', format: 'date-time'
                    }, {
                        name: 'finished', title: 'Completed', type: 'string', format: 'data-time'
                    }, {
                        name: 'enforcement', title: 'Enforcement Set Name', type: 'string'
                    }, {
                        name: 'view', title: 'Triggered Query Name', type: 'string'
                    }, {
                        name: 'period', title: 'Trigger Recurrence', type: 'string'
                    }, {
                        name: 'condition', title: 'Triggered Conditions', type: 'string'
                    }]
                }
            },
            taskResult() {
                if (!this.taskData) return {}
                return this.taskData.result
            },
            mainAction() {
                if (!this.taskResult) return []
                let mainAction = this.taskResult[mainCondition].action
                return {
                    condition: mainCondition, key: mainCondition,
                    name: mainAction['action_name'],
                    title: this.taskResult[mainCondition].name,
                    status: this.getStatus(mainAction),
                    selected: this.actionInView.position && this.actionInView.position.condition === mainCondition
                }
            },
            successiveActions() {
                return [successCondition, failCondition, postCondition].map(condition => {
                    return {
                        condition,
                        items: !this.taskResult ? [] : this.taskResult[condition].map(item => {
                            return {
                                ...item,
                                status: this.getStatus(item.action)
                            }
                        }),
                        selected: this.selectedAction(condition),
                        readOnly: true
                    }
                })
            },
            currentActionName() {
                if (!this.actionInView.definition || !this.actionInView.definition.action
                    || !this.actionInView.position) return ''

                return this.actionInView.definition.action['action_name']
            },
            actionResCard() {
                if (!this.currentActionName) return {}
                return {
                    key: 'actionConf',
                    title: `Action Library / ${actionsMeta[this.currentActionName].title}`,
                    logo: `actions/${this.currentActionName}`
                }
            },
            triggerView() {
                if (!this.taskResult || !this.taskResult.metadata || !this.taskResult.metadata.trigger) return null

                return this.taskResult.metadata.trigger.view
            }
        },
        data() {
            return {
                actionInView: {
                    position: null, definition: null
                }
            }
        },
        methods: {
            ...mapActions({
                fetchTask: FETCH_TASK
            }),
            ...mapMutations({
                updateView: UPDATE_DATA_VIEW
            }),
            initData() {
                if (this.ecFilter && this.ecFilter.condition && this.ecFilter.condition !== mainCondition) {
                    this.selectAction(this.ecFilter.condition, this.ecFilter.i)
                } else {
                    this.selectActionMain()
                }
            },
            getStatus(action) {
                if (!action.results) return 'disabled'
                if (typeof (action.results) === 'string') return 'error'
                if (action.results.successful !== undefined) {
                    return action.results.successful ? 'success' : 'error'
                }

                let successCount = action.results['successful_entities'].length
                let failureCount = action.results['unsuccessful_entities'].length
                if (!failureCount && !successCount) return 'disabled'
                let ratio = successCount / (failureCount + successCount)
                if (ratio === 1) return 'success'
                if (ratio < 0.5) return 'error'
                return 'warning'
            },
            selectAction(condition, i) {
                this.actionInView.position = {condition, i}
                this.actionInView.definition = this.taskResult[condition][i]
            },
            selectActionMain() {
                this.actionInView.position = {condition: mainCondition}
                this.actionInView.definition = this.taskResult.main
            },
            selectedAction(condition) {
                if (!this.actionInView.position || this.actionInView.position.condition !== condition) return -1

                return this.actionInView.position.i
            },
            runFilter(index) {
                let success = index === 0 ? 'successful_entities' : 'unsuccessful_entities'
                let i = this.actionInView.position.i || 0

                this.updateView({
                    module: this.triggerView.entity, view: {
                        ...this.viewObj,
                        ecFilter: {
                            pretty_id: this.taskData.result.metadata.pretty_id,
                            condition: this.actionInView.position.condition,
                            i,
                            success,
                            details: {
                                enforcement: this.name, action: this.actionInView.definition.name, id: this.id
                            }
                        }
                    }
                })
                this.$router.push({path: `/${this.triggerView.entity}`})
            }
        },
        created() {
            if (!this.taskData.name || this.taskData.uuid !== this.id) {
                this.fetchTask(this.id).then(() => {
                    this.initData()
                })
            } else {
                this.initData()
            }

        }
    }
</script>

<style lang="scss">
    .x-task {
        .main {
            height: 100%;
            display: grid;
            grid-template-rows: min-content auto;
            grid-gap: 36px 0;

            .header {
                padding-bottom: 24px;
                border-bottom: 1px solid rgba($theme-orange, 0.2);
            }

            .body {
                display: grid;
                grid-auto-rows: min-content;
                grid-gap: 24px 0;
                overflow: auto;
            }
        }

        .details {
            .x-card {
                height: 100%;

                .x-action-result {
                    height: calc(100% - 72px);
                }
            }
        }

        .array {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-gap: 12px;
        }
    }
</style>