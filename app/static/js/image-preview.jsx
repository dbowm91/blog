export default function initImagePreview() {
    const coverImageInput = document.getElementById('image');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreviewImg = document.getElementById('image-preview-img');
    const removeImageBtn = document.getElementById('remove-image-btn');
    const removeImageLabel = document.getElementById('remove-image-label');
    const removeImageCheckbox = document.getElementById('remove-image-checkbox');

    if (coverImageInput && imagePreviewContainer && imagePreviewImg) {
        coverImageInput.addEventListener('change', () => {
            const file = coverImageInput.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreviewImg.src = e.target.result;
                    imagePreviewImg.style.display = 'block';
                    if (removeImageBtn) {
                        removeImageBtn.textContent = 'Clear';
                    }
                    if (removeImageLabel) {
                        removeImageLabel.style.display = 'inline-flex';
                    }
                };
                reader.readAsDataURL(file);
            }
        });

        if (removeImageBtn) {
            removeImageBtn.addEventListener('click', () => {
                coverImageInput.value = '';
                imagePreviewImg.src = '';
                imagePreviewImg.style.display = 'none';
                removeImageBtn.textContent = 'Remove';
                if (removeImageCheckbox) {
                    removeImageCheckbox.checked = true;
                }
                if (removeImageLabel) {
                    removeImageLabel.style.display = 'none';
                }
});
    }
}