export const vaultProviderEnum = {
  thycotic_secret_server_vault: {
    name: 'thycotic',
    title: 'Thycotic Secret Server',
    schema: {
      type: 'array',
      items: [{
        name: 'secret',
        title: 'Secret ID',
        type: 'integer',
      }, {
        name: 'field',
        title: 'Field Name',
        type: 'string',
        default: 'Password',
      }],
      required: ['secret', 'field'],
    }
  },
  cyberark_vault: {
    name: 'cyberark',
    title: 'CyberArk Vault',
    type: 'array',
    schema: {
      items: [{
        name: 'query',
        title: 'Query',
        type: 'string',
        format: 'text',
      }],
      required: ['query'],
    }
  },
};