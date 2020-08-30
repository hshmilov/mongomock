import Vue from 'vue'

export const xActionsGroup = {
    name: 'XActionItem',
    render(h) {
        return (
            <ul>{this.$slots.default}</ul>
        )
    }
}

export const xActionItem = {
    name: 'XActionItem',
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
        disabled: {
            type: Boolean,
            default: false,
        }
    },
    render(h) {
        return (
            <li onClick={() => this.$emit('click')}>
                <v-icon  size={this.size} color={this.color} disabled={this.disabled}>{this.icon}</v-icon>
            </li>
        )
    }

}
