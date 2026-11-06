import { getCsrfToken, getCsrfHeaderName } from './shared/utils.js';

const CHUNKED_THRESHOLD_BYTES = 8 * 1024 * 1024;
const CHUNK_RETRIES = 3;

function parseJsonError(xhr, fallback) {
    try {
        const data = JSON.parse(xhr.responseText);
        if (data && data.error) return data.error;
    } catch (e) {
        // fall through to the generic message
    }
    return fallback;
}

function chunkedBaseUrl(uploadUrl) {
    return uploadUrl.replace(/\/upload$/, '');
}

function sessionKey(category, file) {
    return `devlog-chunked:${category}:${file.name}:${file.size}:${file.lastModified}`;
}

function readStoredSession(key) {
    try {
        const raw = window.localStorage.getItem(key);
        if (!raw) return null;
        const data = JSON.parse(raw);
        if (data && data.uploadId) return data.uploadId;
    } catch (e) {
        // corrupted entry: start over
    }
    return null;
}

function forgetStoredSession(key) {
    try {
        window.localStorage.removeItem(key);
    } catch (e) {
        // storage unavailable: uploads still work, resume does not
    }
}

function rememberStoredSession(key, uploadId) {
    try {
        window.localStorage.setItem(key, JSON.stringify({ uploadId }));
    } catch (e) {
        // storage unavailable: uploads still work, resume does not
    }
}

function xhrJson(method, url, body) {
    return new Promise((resolve, reject) => {
        const csrfToken = getCsrfToken();
        const xhr = new XMLHttpRequest();
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    resolve(JSON.parse(xhr.responseText));
                } catch (e) {
                    reject(new Error('Upload failed. Please try again.'));
                }
            } else {
                reject(new Error(parseJsonError(xhr, 'Upload failed. Please try again.')));
            }
        });
        xhr.addEventListener('error', () => reject(new Error('Upload failed. Please try again.')));
        xhr.open(method, url);
        xhr.setRequestHeader(getCsrfHeaderName(), csrfToken);
        xhr.setRequestHeader('Accept', 'application/json');
        if (body !== undefined) {
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(JSON.stringify(body));
        } else {
            xhr.send();
        }
    });
}

function putChunk(url, blob, onProgress, onXhr) {
    return new Promise((resolve, reject) => {
        const csrfToken = getCsrfToken();
        const xhr = new XMLHttpRequest();
        if (onXhr) onXhr(xhr);
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) onProgress(e.loaded);
        });
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve();
            } else {
                reject(new Error(parseJsonError(xhr, 'Upload failed. Please try again.')));
            }
        });
        xhr.addEventListener('error', () => reject(new Error('Upload failed. Please try again.')));
        xhr.addEventListener('abort', () => reject(new Error('Upload cancelled.')));
        xhr.open('PUT', url);
        xhr.setRequestHeader(getCsrfHeaderName(), csrfToken);
        xhr.setRequestHeader('Content-Type', 'application/octet-stream');
        xhr.send(blob);
    });
}

export function initUpload() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const uploadCategory = document.getElementById('upload-category');

    if (uploadZone && fileInput && uploadCategory) {
        let uploadErrorTimer;
        let activeSession = null;

        const showUploadError = (message) => {
            clearTimeout(uploadErrorTimer);
            const existing = uploadZone.querySelector('.form-error');
            if (existing) existing.remove();
            const errorEl = document.createElement('div');
            errorEl.className = 'form-error';
            errorEl.textContent = message;
            uploadZone.appendChild(errorEl);
            uploadErrorTimer = setTimeout(() => errorEl.remove(), 8000);
        };

        const hideUploadError = () => {
            clearTimeout(uploadErrorTimer);
            const existing = uploadZone.querySelector('.form-error');
            if (existing) existing.remove();
        };

        const showUploadProgress = (percent) => {
            hideUploadError();
            let progressBar = uploadZone.querySelector('.upload-progress');
            let progressText = uploadZone.querySelector('.upload-progress-text');
            if (!progressBar) {
                progressBar = document.createElement('div');
                progressBar.className = 'upload-progress';
                const progressFill = document.createElement('div');
                progressFill.className = 'upload-progress-fill';
                progressBar.appendChild(progressFill);
                uploadZone.appendChild(progressBar);
            }
            if (!progressText) {
                progressText = document.createElement('div');
                progressText.className = 'upload-progress-text';
                uploadZone.appendChild(progressText);
            }
            const progressFill = progressBar.querySelector('.upload-progress-fill');
            if (progressFill) {
                progressFill.style.width = `${percent}%`;
            }
            progressText.textContent = `${percent}%`;
            progressBar.style.display = 'block';
            progressText.style.display = 'block';
        };

        const hideUploadProgress = () => {
            const progressBar = uploadZone.querySelector('.upload-progress');
            const progressText = uploadZone.querySelector('.upload-progress-text');
            if (progressBar) progressBar.remove();
            if (progressText) progressText.remove();
        };

        const cancelActiveUpload = () => {
            if (activeSession) {
                const session = activeSession;
                activeSession = null;
                if (session.abortXhr) session.abortXhr();
                if (session.uploadId) {
                    const base = chunkedBaseUrl(uploadZone.dataset.uploadUrl);
                    xhrJson('DELETE', `${base}/chunked/${session.uploadId}`).catch(() => {});
                }
                if (session.key) forgetStoredSession(session.key);
            }
        };

        const handleSingleUpload = (file) => {
            hideUploadProgress();
            showUploadProgress(0);

            const csrfToken = getCsrfToken();
            const formData = new FormData();
            formData.append('csrf_token', csrfToken);
            formData.append('file', file);
            formData.append('category', uploadCategory.value);

            const xhr = new XMLHttpRequest();
            activeSession = {
                abortXhr: () => xhr.abort(),
                uploadId: null,
                key: null,
            };

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    showUploadProgress(percent);
                }
            });

            xhr.addEventListener('load', () => {
                activeSession = null;
                if (xhr.status >= 200 && xhr.status < 300) {
                    hideUploadProgress();
                    window.location.reload();
                } else {
                    hideUploadProgress();
                    showUploadError(parseJsonError(xhr, 'Upload failed. Please try again.'));
                }
            });

            xhr.addEventListener('error', () => {
                activeSession = null;
                hideUploadProgress();
                showUploadError('Upload failed. Please try again.');
            });

            xhr.addEventListener('abort', () => {
                activeSession = null;
                hideUploadProgress();
                showUploadError('Upload cancelled.');
            });

            xhr.open('POST', uploadZone.dataset.uploadUrl);
            xhr.setRequestHeader(getCsrfHeaderName(), csrfToken);
            xhr.setRequestHeader('Accept', 'application/json');
            xhr.send(formData);
        };

        const handleChunkedUpload = async (file) => {
            const category = uploadCategory.value;
            const base = chunkedBaseUrl(uploadZone.dataset.uploadUrl);
            const key = sessionKey(category, file);
            hideUploadProgress();
            showUploadProgress(0);

            let cancelled = false;
            let currentXhr = null;
            activeSession = {
                abortXhr: () => {
                    cancelled = true;
                    if (currentXhr) currentXhr.abort();
                },
                uploadId: null,
                key,
            };

            const fail = (message) => {
                activeSession = null;
                hideUploadProgress();
                showUploadError(message);
            };

            try {
                let uploadId = readStoredSession(key);
                let plan = null;
                if (uploadId) {
                    try {
                        plan = await xhrJson('GET', `${base}/chunked/${uploadId}`);
                        if (plan.size !== file.size || plan.category !== category) {
                            plan = null;
                            uploadId = null;
                        } else {
                            activeSession.uploadId = uploadId;
                        }
                    } catch (e) {
                        plan = null;
                        uploadId = null;
                    }
                }
                if (!plan) {
                    const init = await xhrJson('POST', `${base}/chunked/init`, {
                        filename: file.name,
                        size: file.size,
                        category,
                    });
                    uploadId = init.upload_id;
                    rememberStoredSession(key, uploadId);
                    activeSession.uploadId = uploadId;
                    plan = await xhrJson('GET', `${base}/chunked/${uploadId}`);
                }

                const chunkSize = plan.chunk_size;
                let done = plan.received.filter(Boolean).length;
                showUploadProgress(Math.round((done / plan.total_chunks) * 100));

                for (let index = 0; index < plan.total_chunks; index += 1) {
                    if (cancelled) {
                        fail('Upload cancelled.');
                        return;
                    }
                    if (plan.received[index]) continue;
                    const start = index * chunkSize;
                    const blob = file.slice(start, Math.min(start + chunkSize, file.size));
                    let sent = false;
                    for (let attempt = 0; attempt < CHUNK_RETRIES && !sent; attempt += 1) {
                        if (cancelled) {
                            fail('Upload cancelled.');
                            return;
                        }
                        try {
                            await putChunk(
                                `${base}/chunked/${uploadId}/${index}`,
                                blob,
                                (loaded) => {
                                    const overall = (done * chunkSize + loaded) / file.size;
                                    showUploadProgress(Math.min(99, Math.round(overall * 100)));
                                },
                                (xhr) => {
                                    currentXhr = xhr;
                                },
                            );
                            currentXhr = null;
                            sent = true;
                        } catch (e) {
                            currentXhr = null;
                            if (cancelled) {
                                fail('Upload cancelled.');
                                return;
                            }
                            if (attempt + 1 >= CHUNK_RETRIES) {
                                const status = await xhrJson(
                                    'GET',
                                    `${base}/chunked/${uploadId}`,
                                ).catch(() => null);
                                if (status && status.received[index]) {
                                    sent = true;
                                } else {
                                    fail(e.message || 'Upload failed. Please try again.');
                                    return;
                                }
                            }
                        }
                    }
                    done += 1;
                    showUploadProgress(Math.min(99, Math.round((done / plan.total_chunks) * 100)));
                }

                if (cancelled) {
                    fail('Upload cancelled.');
                    return;
                }
                await xhrJson('POST', `${base}/chunked/${uploadId}/complete`);
                activeSession = null;
                forgetStoredSession(key);
                hideUploadProgress();
                window.location.reload();
            } catch (e) {
                activeSession = null;
                hideUploadProgress();
                showUploadError((e && e.message) || 'Upload failed. Please try again.');
            }
        };

        const handleUpload = (file) => {
            cancelActiveUpload();
            if (uploadCategory.value !== 'image' && file.size > CHUNKED_THRESHOLD_BYTES) {
                handleChunkedUpload(file);
            } else {
                handleSingleUpload(file);
            }
        };

        const updateAcceptedTypes = () => {
            fileInput.accept = uploadCategory.value === 'image'
                ? 'image/png,image/jpeg,image/gif,image/webp'
                : uploadCategory.value === 'video'
                    ? 'video/mp4,video/webm,.mp4,.webm'
                    : '';
        };
        uploadCategory.addEventListener('change', updateAcceptedTypes);
        updateAcceptedTypes();

        uploadZone.addEventListener('click', (event) => {
            if (event.target !== fileInput) fileInput.click();
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                handleUpload(fileInput.files[0]);
            }
        });

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                handleUpload(e.dataTransfer.files[0]);
            }
        });
    }
}

export default initUpload;
