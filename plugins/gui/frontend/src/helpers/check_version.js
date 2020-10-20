import axios from 'axios';

const isDevEnv = process.env.NODE_ENV === 'none' || process.env.NODE_ENV === 'development';

export default function CheckVersion() {
  const currentHash = '{{POST_BUILD_ENTERS_HASH_HERE}}';
  let newHash = '';

  const hasHashChanged = () => {
    if (!currentHash || currentHash === '{{POST_BUILD_ENTERS_HASH_HERE}}') {
      return true;
    }

    return currentHash !== newHash;
  };
  const reloadApp = () => {
    window.location.reload();
  };
  const checkVersion = async () => {
    try {
      const fileResponse = await axios.get(`/dist/version.json?t=${new Date().getTime()}`);

      newHash = fileResponse.data.hash;

      if (hasHashChanged()) {
        reloadApp();
      }
    } catch (error) {
      // if there is an error then the initVersionCheck will check again the version
    }
  };
  const initVersionCheck = (frequency = 1000 * 60 * 10) => {
    if (!isDevEnv) {
      setTimeout(() => {
        checkVersion().then(() => {
          initVersionCheck();
        });
      }, frequency);
    }
  };


  return {
    initVersionCheck,
  };
}
