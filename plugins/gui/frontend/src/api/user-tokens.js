import createRequest from './create-request';

export const validateResetPasswordToken = async (token) => {
  const uri = `settings/users/tokens/validate/reset_password/${token}`;
  const request = createRequest(uri);
  const { data } = await request({});
  return data;
};

export const resetUserPasswordByToken = async (token, newPassword) => {
  const uri = 'settings/users/tokens/reset_password';
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

export const getUserResetPasswordLink = async (userId, invite) => {
  const uri = 'settings/users/tokens/create/reset_password';
  const request = createRequest(uri);
  const requestOptions = {};
  // If this link is for invitation then use the 'PUT' method
  requestOptions.method = invite ? 'PUT' : 'POST';
  requestOptions.data = {
    user_id: userId,
  };
  const { data } = await request(requestOptions);
  return data;
};

export const sendResetPasswordTokenEmail = async (userId, email, invite) => {
  const uri = 'settings/users/tokens/send_reset_password';
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
