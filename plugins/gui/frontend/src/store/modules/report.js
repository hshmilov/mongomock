import { REQUEST_API } from '../actions'

export const DOWNLOAD_REPORT = 'DOWNLOAD_REPORT'
export const report = {
	state: {},
	actions: {
		[ DOWNLOAD_REPORT ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: 'export_report'
			}).then((response) => {
				let blob = new Blob([response.data], { type: response.headers["content-type"]} )
				let link = document.createElement('a')
				link.href = window.URL.createObjectURL(blob)
				link.download = 'axonius_report.pdf'
				link.click()
			})
		}
	}
}