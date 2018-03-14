export default {
	methods: {
		getData(data, path) {
			if (!data) return ''

			if (!Array.isArray(data)) {
				let firstDot = path.indexOf('.')
				if (firstDot === -1) return data[path]
				return this.getData(data[path.substring(0, firstDot)], path.substring(firstDot + 1))
			}
			if (data.length === 1) return this.getData(data[0], path)

			let children = []
			data.forEach((item) => {
				let child = this.getData(item, path)
				if (!child) return

				let basicChildren = children.map((child) => this.getDataBasic(child))
				if (Array.isArray(child)) {
					children = children.concat(child.filter(
						(childItem => !this.matchArrayPrefix(basicChildren, this.getDataBasic(childItem)))))
				} else if (!this.matchArrayPrefix(basicChildren, this.getDataBasic(child))) {
					children.push(child)
				}
			})
			return Array.from(children)
		},
		matchArrayPrefix(array, prefix) {
			if (!prefix || typeof prefix !== 'string') return false
			prefix = prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
			return array.some(item => (item.match(`^${prefix}`) !== null))
		},
		getDataBasic(data) {
			if (typeof data === 'string') return data.toLowerCase()
			return data
		}
	}
}