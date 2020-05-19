export const vaultProviderEnum = {
  thycotic_secret_server_vault: {
    name: 'thycotic',
    title: 'Thycotic Secret Server',
    schema: {
      title: 'Secret ID',
      type: 'integer',
      required: true,
    },
  },
  cyberark_vault: {
    name: 'cyberark',
    title: 'CyberArk Vault',
    schema: {
      title: 'Query',
      type: 'string',
      format: 'text',
      required: true,
    },
  },
};