
import { defaultFields } from '../../constants/entities'

export const users = {
    state: {
        content: {data: [], fetching: false, error: ''},

        count: {data: 0, fetching: false, error: ''},

        view: {
            page: 0, pageSize: 20, fields: defaultFields.users, coloumnSizes: [], query: {
                filter: '', expressions: [], search: ''
            }, sort: {
                field: '', desc: true
            },
            historical: null
        },

        details: { data: {}, fetching: false, error: '' },

        fields: {data: [], fetching: false, error: ''},

        hyperlinks: {data: [], fetching: false, error: ''},

        views: {
            content: { data: [], fetching: false, error: '', rule: ''},
            count: { data: 0, fetching: false, error: ''},
            view: {
                page: 0, pageSize: 20, query: {
                    filter: '', expressions: [], search: ''
                }, sort: {
                    field: '', desc: true
                }
            },

            saved: {data: [], fetching: false, error: ''},

            history: {data: [], fetching: false, error: ''}
        },

        labels: {data: [], fetching: false, error: ''},

        current: {
            id: '',

            fetching: false, data: {}, error: '',

            tasks: {
                fetching: false, data: [], error: ''
            }
        }
    }
}