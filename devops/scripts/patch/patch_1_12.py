#!/usr/bin/env python3

import sys
import os.path
import subprocess
import shlex

from pathlib import Path

HOME = Path('.')
CORTEX_PATH = Path(HOME, 'cortex')
MARKER = Path(HOME, f'{os.path.basename(__file__)}.marker')


def is_marker_present(marker_path):
    return Path(marker_path).is_file()


def put_marker(marker_path):
    Path(marker_path).touch()


def patch_file(dest_file, content):
    dest_file.write_text(content)


FILE_1 = Path(CORTEX_PATH, 'plugins/gui/frontend/src/components/data/DataEntitiesTable.vue')
FILE_1_CONTENT = '''<template>
    <div class="x-data-entities">
        <x-historical-date-picker v-model="historical" />
        <x-data-query :module="module" :read-only="isReadOnly" />
        <x-data-table :module="module" id-field="internal_axon_id" ref="table" @click-row="configEntity"
                      v-model="isReadOnly? undefined: selected" @data="$emit('data', $event)">
            <template slot="actions">
                <x-data-entity-actions v-show="selected && selected.length" :module="module" :entities="selected" @done="updateEntities" />
                <!-- Modal for selecting fields to be presented in table, including adapter hierarchy -->
                <x-data-field-menu :module="module" />
                <div class="x-btn link" @click="exportCSV">Export CSV</div>
            </template>
        </x-data-table>
    </div>
</template>

<script>
    import xHistoricalDatePicker from '../../components/inputs/HistoricalDatePicker.vue'
    import xDataQuery from '../../components/data/DataQuery.vue'
    import xDataTable from '../../components/tables/DataTable.vue'
    import xDataEntityActions from '../../components/data/DataEntityActions.vue'
    import xDataFieldMenu from '../../components/data/DataFieldMenu.vue'

    import { mapState, mapMutations, mapActions } from 'vuex'
    import { UPDATE_DATA_VIEW } from '../../store/mutations';
    import { FETCH_DATA_CONTENT_CSV } from '../../store/actions'

    export default {
        name: 'data-entities-table',
        components: { xHistoricalDatePicker, xDataQuery, xDataTable, xDataEntityActions, xDataFieldMenu },
        props: { module: { required: true } },
        computed: {
            ...mapState({
                isReadOnly(state) {
                    if (!state.auth.data || !state.auth.data.permissions) return true
                    return state.auth.data.permissions.Users === 'ReadOnly'
                },
                historicalState(state) {
                    return state[this.module].view.historical
                },
                allowedDates(state) {
                    return state.constants.allowedDates[this.module]
                }
            }),
            historical: {
                get() {
                    if (!this.historicalState) return null
                    return this.historicalState.substring(0, 10)
                },
                set(newDate) {
                    this.updateView({
                        module: this.module, view: {
                            historical: this.allowedDates[newDate]
                        }
                    })
                }
            }
        },
        data() {
            return {
                selected: []
            }
        },
        methods: {
            ...mapMutations({ updateView: UPDATE_DATA_VIEW }),
            ...mapActions({
                fetchContentCSV: FETCH_DATA_CONTENT_CSV
            }),
            configEntity (entityId) {
                if (this.selected && this.selected.length) return

                let path = `${this.module}/${entityId}`
                if (this.historicalState) {
                    path += `?history=${encodeURIComponent(this.historicalState)}`
                }
                this.$router.push({path: path})
            },
            updateEntities() {
                this.$refs.table.fetchContentPages()
                this.selected = []
            },
            exportCSV() {
                this.fetchContentCSV({ module: this.module })
            }
        }
    }
</script>

<style lang="scss">
    .x-data-entities {
        height: calc(100% - 24px);
    }
</style>
'''


def main():
    try:
        if is_marker_present(MARKER):
            print(f'Marker already present - {MARKER}')
            sys.exit(0)
        print(f'Patching - {MARKER}')

        patch_file(FILE_1, FILE_1_CONTENT)

        subprocess.run(shlex.split('./axonius.sh service gui up --restart --hard --rebuild'), cwd=CORTEX_PATH)

        print(f'Patching done - {MARKER}')
    finally:
        put_marker(MARKER)


if __name__ == '__main__':
    main()
