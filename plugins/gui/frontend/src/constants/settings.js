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
  aws_secrets_manager_vault: {
    name: 'aws',
    title: 'AWS Secrets Manager',
    type: 'array',
    schema: {
      items: [{
        name: 'name',
        title: 'Secret name',
        type: 'string',
      },
	  {
        name: 'secret_key',
        title: 'Secret key',
        type: 'string',
      }],
      required: ['name', 'secret_key'],
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

export const tunnelConnectionStatuses = {
  connected: 'connected',
  disconnected: 'disconnected',
  notAvailable: 'not_available',
  neverConnected: 'never_connected',
};

export const emptyScheme = {
  name: 'empty',
  type: 'array',
  items: [],
};
