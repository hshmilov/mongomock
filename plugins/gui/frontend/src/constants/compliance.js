export const emailFormFields = {
  aws: [
    {
      name: 'mailSubject',
      title: 'Email Subject',
      type: 'string',
      required: true,
    },
    {
      name: 'mailMessage',
      title: 'Custom message (up to 500 characters)',
      type: 'string',
      format: 'text',
      limit: 500,
      required: false,
    },
    {
      name: 'accountAdmins',
      title: 'Send to AWS account admins',
      type: 'bool',
      format: 'text',
      required: true,
    },
    {
      name: 'emailList',
      title: 'Recipients',
      type: 'array',
      items: {
        type: 'string',
        format: 'email',
      },
      required: false,
    },
    {
      name: 'emailListCC',
      title: 'Recipients CC',
      type: 'array',
      items: {
        type: 'string',
        format: 'email',
      },
      required: false,
    },
  ],
  azure: [
    {
      name: 'mailSubject',
      title: 'Email Subject',
      type: 'string',
      required: true,
    },
    {
      name: 'mailMessage',
      title: 'Custom message (up to 500 characters)',
      type: 'string',
      format: 'text',
      limit: 500,
      required: false,
    },
    {
      name: 'emailList',
      title: 'Recipients',
      type: 'array',
      items: {
        type: 'string',
        format: 'email',
      },
      required: false,
    },
    {
      name: 'emailListCC',
      title: 'Recipients CC',
      type: 'array',
      items: {
        type: 'string',
        format: 'email',
      },
      required: false,
    },
  ],
};

export const jiraFormFields = {
  items: ['project_key', 'issue_type', 'incident_title', 'incident_description', 'assignee',
    'labels', 'components',
  ],
  required: [
    'incident_description',
    'project_key',
    'incident_title',
    'issue_type',
  ],
};
