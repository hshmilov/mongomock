import axios_client from '@api/axios';
import createRequest from './create-request';

export const executeFile = async (fileServerId) => {
  const uri = `/upload_file/execute/${fileServerId}`;
  const request = createRequest(uri);

  const requestOptions = {
    method: 'POST',
  };
  const res = await request(requestOptions);
  return res.data;
};

// this method override file pond process file function in a specific case
// our case is chunk upload, its designed to upload one file chunk by chunk
// with a retry logic of 3 times
export const processFileUploadInChunks = (
  fieldName, file, metadata, load, error, progress, abort, transfer,
) => {
  const chunkSize = 1024 * 1024 * 100;
  const fileSize = file.size;
  const totalChunks = Math.ceil(fileSize / chunkSize);
  let currentChunk = 0;
  let shouldAbort = false;
  axios_client({
    method: 'post',
    url: '/upload_file',
    data: file.name,
    headers: {
      'Upload-Length': file.size,
    },
  }).then(async (response) => {
    // passing the file id to FilePond
    progress(true, 0, file.size);
    const fileId = response.data;
    let retryCount = 0;
    while (currentChunk < totalChunks) {
      try {
        if (shouldAbort) {
          abort();
          break;
        }
        const offset = currentChunk * chunkSize;
        const chunk = file.slice(offset, offset + chunkSize, 'application/offset+octet-stream');
        // eslint-disable-next-line no-await-in-loop
        const result = await axios_client({
          method: 'patch',
          url: `/upload_file?patch=${fileId}`,
          data: chunk,
          headers: {
            'Content-Type': 'application/offset+octet-stream',
            'Upload-Offset': offset,
            'Upload-Length': file.size,
            'Upload-Name': file.name,
          },
        });
        progress(true, offset + chunkSize, file.size);
        currentChunk += 1;
        transfer(result.data);
      } catch (e) {
        if (retryCount > 3) {
          error({
            type: 'error',
            body: 'max retries exceeded',
          });
          throw e;
        }
        retryCount += 1;
      }
    }
    if (currentChunk === totalChunks) {
      load(fileId);
    } else {
      error({
        type: 'error',
        body: 'operation aborted',
      });
    }
  }).catch((e) => {
    error({
      type: 'error',
      body: `something went wrong :${e}`,
    });
  });
  // Should expose an abort method so the request can be cancelled
  return {
    abort: () => {
      shouldAbort = true;
    },
  };
};
