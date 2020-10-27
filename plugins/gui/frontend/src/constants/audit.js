// eslint-disable-next-line import/prefer-default-export
export const auditFields = [
  {
    name: 'type',
    title: 'Type',
    type: 'string',
    format: 'icon',
    iconTooltip: {
      user: 'User',
      error: 'Error',
      info: 'Info',
    },
  },
  {
    name: 'date',
    title: 'Date',
    type: 'string',
    format: 'date-time',
  },
  {
    name: 'user',
    title: 'User',
    type: 'string',
  },
  {
    name: 'action',
    title: 'Action',
    type: 'string',
  },
  {
    name: 'category',
    title: 'Category',
    type: 'string',
  },
  {
    name: 'message',
    title: 'Message',
    type: 'string',
  },
];
