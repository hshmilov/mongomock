import createRequest from './create-request';

export const validateResetPasswordToken = async (token) => {
  const uri = `settings/users/tokens/validate/${token}`;
  const request = createRequest(uri);
  const { data } = await request({});
  return data;
};

export const resetUserPasswordByToken = async (token, newPassword) => {
  const uri = 'settings/users/tokens/reset';
  const request = createRequest(uri);
  const requestOptions = {};
  requestOptions.method = 'POST';
  requestOptions.data = {
    password: newPassword,
    token,
  };
  const { data } = await request(requestOptions);
  return data;
};

export const getUserResetPasswordLink = async (userId, invite, userName) => {
  const uri = 'settings/users/tokens/generate';
  const request = createRequest(uri);
  const requestOptions = {};
  // If this link is for invitation then use the 'PUT' method
  requestOptions.method = invite ? 'PUT' : 'POST';
  requestOptions.data = {
    user_id: userId,
    user_name: userName,
  };
  const { data } = await request(requestOptions);
  return data;
};

export const sendResetPasswordTokenEmail = async (userId, email, invite) => {
  const uri = 'settings/users/tokens/notify';
  const request = createRequest(uri);
  const requestOptions = {};
  // If this link is for invitation then use the 'PUT' method
  requestOptions.method = invite ? 'PUT' : 'POST';
  requestOptions.data = {
    user_id: userId,
    email,
    invite,
  };
  const { data } = await request(requestOptions);
  return data;
};
