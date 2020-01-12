import createRequest from './create-request';
import { EntitiesEnum as Entities } from '../constants/entities';

const fetchDevicesTags = async () => {
  const uri = '/devices/views/tags';
  const request = createRequest(uri);
  const requestOptions = {};
  const res = await request(requestOptions);
  return res.data;
};

const fetchUsersTags = async () => {
  const uri = '/users/views/tags';
  const request = createRequest(uri);

  const requestOptions = {};
  const res = await request(requestOptions);
  return res.data;
};

export const featchEntityTags = async (entity) => {
  let res;
  if (entity === Entities.devices) {
    res = await fetchDevicesTags();
  } else if (entity === Entities.users) {
    res = await fetchUsersTags();
  }
  return res;
};

const fetchDevicesSavedQueriesNames = async () => {
  const uri = '/devices/views/names_list';
  const request = createRequest(uri);

  const requestOptions = {};
  const res = await request(requestOptions);
  return res.data;
};

const fetchUsersSavedQueriesNames = async () => {
  const uri = '/users/views/names_list';
  const request = createRequest(uri);

  const requestOptions = {};
  const res = await request(requestOptions);
  return res.data;
}

export const featchEntitySavedQueriesNames = async (entity) => {
  let res;

  if (entity === Entities.devices) {
    res = await fetchDevicesSavedQueriesNames();
  } else if (entity === Entities.users) {
    res = await fetchUsersSavedQueriesNames();
  }
  return res;
};
