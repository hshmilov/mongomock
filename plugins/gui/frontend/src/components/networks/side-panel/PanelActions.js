import Vue from 'vue'

export const xActionsGroup = {
    name: 'xActionItem',
    render(h) {
        return (
            <ul>{this.$slots.default}</ul>
        )
    }
}

export const xActionItem = {
    name: 'xActionItem',
    props: {
        color: {
            type: String,
            default: '#fff'
        },
        size: {
            type: String,
            default: '20'
        },
        icon: {
            required: true
        },
    },
    render(h) {
        return (
            <li onClick={() => this.$emit('click')}>
                <v-icon  size={this.size} color={this.color}>{this.icon}</v-icon>
            </li>
        )
    }

}
