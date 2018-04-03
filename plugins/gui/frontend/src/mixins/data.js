export default {
	methods: {
		getData(data, path) {
			if (!data) return ''

			if (!Array.isArray(data)) {
				let firstDot = path.indexOf('.')
				if (firstDot === -1) {
					return data[path] ? data[path] : ''
				}
				let prefix = path.substring(0, firstDot)
				// return this.getData((data[prefix]? data[prefix] : data), path.substring(firstDot + 1))
				return this.getData(data[prefix], path.substring(firstDot + 1))
			}
			if (data.length === 1) return this.getData(data[0], path)

			let children = []
			data.forEach((item) => {
				let child = this.getData(item, path)
				if (!child) return

				let basicChildren = children.map((child) => this.getDataBasic(child))
				if (Array.isArray(child)) {
					children = children.concat(child.filter(
						(childItem => !this.arrayContains(basicChildren, this.getDataBasic(childItem)))))
				} else if (!this.arrayContains(basicChildren, this.getDataBasic(child))) {
					children.push(child)
				}
			})
			return Array.from(children)
		},
		arrayContains(array, prefix) {
			if (prefix && typeof prefix === 'string') {
				let escapedPrefix = prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
				return array.some(item => {
					let escapedItem = item.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
					return (item.match(`^${escapedPrefix}`) !== null || prefix.match(`^${escapedItem}`))
				})
			}
			if (prefix && typeof prefix === 'number') {
				return array.includes(prefix)
			}
			return false
		},
		getDataBasic(data) {
			if (typeof data === 'string') return data.toLowerCase()
			return data
		}
	}
}