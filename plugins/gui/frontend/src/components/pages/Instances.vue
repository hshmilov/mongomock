<template>
    <x-page title="instances" class="x-instances">
        <x-table-wrapper title="Edit, Deactivate or Reactivate Instances" :loading="loading">
            <template slot="actions">
                <x-button id="get-connection-string" @click="connecting= !connecting" :disabled="isReadOnly">Connect Node</x-button>
                <x-button link v-if="showActivationOption === 'Activated'" @click="deactivateServers">Deactivate</x-button>
                <x-button link v-if="showActivationOption === 'Deactivated'" @click="reactivateServers">Reactivate</x-button>
            </template>
            <x-table v-if="instances" slot="table" id-field="node_id" :data="instances" :fields="fields"
                     v-model="isReadOnly ? undefined : selectedInstance"
                     :on-click-row="isReadOnly ? undefined : showNameChangeModal"/>
        </x-table-wrapper>
        <x-modal v-if="renaming" @close="closeNameChange" @confirm="instanceNameChange" approve-text="Change Name">
            <div slot="body">How do you want to name this instance?<br/><br/>
                <input class="form-control" id="instanceName" v-model="newInstanceName">
            </div>
        </x-modal>
        <x-modal v-if="connecting && !isReadOnly" @close="connecting= !connecting" @confirm="connecting= !connecting">
            <div slot="body">How to connect a new node<br/><br/>
                1. Deploy another Axonius machine on the required subnet.<br/>
                2. Log in to that machine via ssh with these credentials: node_maker:M@ke1tRain<br/>
                3. Paste a connection string that looks like (with spaces): {{ hostIP }} {{ connectionEncriptionKey }}
                &lt;User-Nickname&gt;
            </div>
            <div slot="footer">
                <x-button @click="connecting= !connecting">OK</x-button>
            </div>
            <button>Copy To Clipboard</button>
        </x-modal>
    </x-page>
</template>

<script>
    import xPage from '../axons/layout/Page.vue'
    import xTableWrapper from '../axons/tables/TableWrapper.vue'
    import xTable from '../axons/tables/Table.vue'
    import xButton from '../axons/inputs/Button.vue'
    import xModal from '../axons/popover/Modal.vue'
    import axios from 'axios'

    import {mapState, mapMutations, mapActions} from 'vuex'
    import {REQUEST_API} from '../../store/actions'
    import {SHOW_TOASTER_MESSAGE} from "../../store/mutations";

    export default {
        name: 'x-instances',
        components: {xPage, xTableWrapper, xTable, xButton, xModal},
        computed: {
            ...mapState({
                isReadOnly(state) {
                    let user = state.auth.currentUser.data
                    if (!user || !user.permissions) return true
                    return user.permissions.Instances === 'ReadOnly'
                }
            }),
            fields() {
                return [
                    {name: 'node_name', title: 'Name', type: 'string'},
                    {name: 'hostname', title: 'Hostname', type: 'string'},
                    {name: 'ips', title: 'IP', type: 'array', items: {type: 'string'}},
                    {name: 'last_seen', title: 'Last Seen', type: 'string', format: 'date-time'},
                    {name: 'status', title: 'Status', type: 'string'},
                    {name: 'node_user_password', title: 'Instance Connect User Password', type: 'string'}
                ]
            },
            hostIP() {
                return this.machineIP
            },
            connectionEncriptionKey() {
                return this.connectionKey
            },
            showActivationOption() {
                if (!this.selectedInstance || this.selectedInstance.length !== 1) return ''
                let selected_instance = this.instances.find(instance => instance.node_id === this.selectedInstance[0])
                return selected_instance.status
            }
        },
        data() {
            return {
                loading: true,
                selectedInstance: [],
                instances: null,
                renaming: false,
                connecting: false,
                newInstanceName: '',
                machineIP: '',
                connectionKey: '',
                instanceChangeId: null
            }
        },
        methods: {
            ...mapMutations({showToasterMessage: SHOW_TOASTER_MESSAGE}),
            ...mapActions({fetchData: REQUEST_API}),
            instanceNameChange() {
                axios.post('/api/instances', {
                    node_id: this.instanceChangeId,
                    key: 'node_name',
                    value: this.newInstanceName
                }).then(() => {
                    this.loading = true
                    this.loadData()
                    this.renaming = false
                })
                this.instanceChangeId = null
                this.newInstanceName = ''
            },
            showNameChangeModal(instanceId) {
                this.instanceChangeId = instanceId
                this.renaming = true
            },
            deactivateServers() {
                if (this.isReadOnly) return
                this.$safeguard.show({
                    text: `
                  Are you sure you want to deactivate this instance?<br/><br/>
                  This will remove all the adapter connections utilizing this instance.
                  `,
                    confirmText: 'Deactivate',
                    onConfirm: () => {
                        this.doDeactivateServers()
                    }
                })
            },
            reactivateServers(){
                if (this.isReadOnly) return
                this.$safeguard.show({
                    text: `
                  Are you sure you want to reactivate this instance?<br/>
                  `,
                    confirmText: 'Reactivate',
                    onConfirm: () => {
                        this.doReactivateServers()
                    }
                })
            },
            doReactivateServers(){
                axios.post('/api/instances', {
                    'node_id': this.selectedInstance[0],
                    'key': 'status',
                    'value': 'Activated'
                }).then(() => this.loadData())
            },
            doDeactivateServers() {
                this.fetchData({
                    rule: 'instances',
                    method: 'DELETE',
                    data: {nodeIds: this.selectedInstance}
                }).then(() => {
                    this.loadData()
                }).catch((errorResponse) => {
                    this.showToasterMessage({ message: errorResponse.response.data.message})
                })
            },
            closeNameChange() {
                this.instanceChangeId = null
                this.newInstanceName = ''
                this.renaming = false
            },
            loadData() {
                this.fetchData({
                    rule: 'instances',
                    method: 'GET'
                }).then((response) => {
                    if (response.data) {
                        this.instances = response.data.instances
                        this.machineIP = response.data.connection_data.host
                        this.connectionKey = response.data.connection_data.key
                        this.loading = false
                    }
                })
            }
        },
        created() {
            this.loadData()
        }
    }
</script>

<style lang="scss">
    .x-instances {
        .x-modal .modal-container {
            position: relative;
            width: auto;
        }
    }
</style>