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

export const generateCSRAction = 'generateCSR';
export const importCertAndKeyAction = 'importCertAndKey';
export const importCSRAction = 'importCSR';
export const resetSystemDefaultsAction = 'resetSystemDefaults';

export const passwordPolicyFormatterEnum = {
  password_length: (value) => `Minimum ${value} character`,
  password_min_lowercase: (value) => `${value} lowercase letter`,
  password_min_uppercase: (value) => `${value} uppercase letter`,
  password_min_numbers: (value) => `${value} number`,
  password_min_special_chars: (value) => `${value} special character`,
};
