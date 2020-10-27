import dayjs from 'dayjs';
import { DEFAULT_DATE_FORMAT } from './modules/constants';

// eslint-disable-next-line import/prefer-default-export
export const parseDateFromAllowedDates = (date, allowedDates) => {
  // this method take user friendly date and return the relevant date known by the system
  const isFormattedToDefault = dayjs(date, DEFAULT_DATE_FORMAT)
    .format(DEFAULT_DATE_FORMAT) === date;
  if (isFormattedToDefault && allowedDates[date]) {
    return allowedDates[date];
  }
  return date;
};
