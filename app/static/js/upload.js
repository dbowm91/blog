import { getCsrfToken, getCsrfHeaderName } from './shared/utils.js';

export function initUpload() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const uploadCategory = document.getElementById('upload-category');

    if (uploadZone && fileInput && uploadCategory) {
        let uploadErrorTimer;

        const showUploadError = (message) => {
            clearTimeout(uploadErrorTimer);
            const existing = uploadZone.querySelector('.form-error');
            if (existing) existing.remove();
            const errorEl = document.createElement('div');
            errorEl.className = 'form-error';
            errorEl.textContent = message;
            uploadZone.appendChild(errorEl);
            uploadErrorTimer = setTimeout(() => errorEl.remove(), 5000);
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

        const handleUpload = (file) => {
            hideUploadProgress();
            showUploadProgress(0);

            const csrfToken = getCsrfToken();
            const formData = new FormData();
            formData.append('csrf_token', csrfToken);
            formData.append('file', file);
            formData.append('category', uploadCategory.value);

            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    showUploadProgress(percent);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    hideUploadProgress();
                    window.location.reload();
                } else {
                    hideUploadProgress();
                    showUploadError('Upload failed. Please try again.');
                }
            });

            xhr.addEventListener('error', () => {
                hideUploadProgress();
                showUploadError('Upload failed. Please try again.');
            });

            xhr.addEventListener('abort', () => {
                hideUploadProgress();
                showUploadError('Upload cancelled.');
            });

            xhr.open('POST', uploadZone.dataset.uploadUrl);
            xhr.setRequestHeader(getCsrfHeaderName(), csrfToken);
            xhr.setRequestHeader('Accept', 'application/json');
            xhr.send(formData);
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