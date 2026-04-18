export function initBulk() {
    // --- Bulk Select All ---
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        const bulkActions = document.getElementById('bulk-actions');
        const checkboxes = document.querySelectorAll('.bulk-checkbox');

        function updateBulkActions() {
            const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
            bulkActions.classList.toggle('hidden', !anyChecked);

            const srAnnounce = document.getElementById('sr-announce');
            if (anyChecked && srAnnounce) {
                const form = document.getElementById('bulk-form');
                const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
                const itemType = form?.dataset.bulkSelect || 'item';
                srAnnounce.textContent = `${checkedCount} ${itemType}${checkedCount === 1 ? '' : 's'} selected`;
            }
        }

        selectAllCheckbox.addEventListener('change', () => {
            checkboxes.forEach(cb => {
                cb.checked = selectAllCheckbox.checked;
            });
            updateBulkActions();
        });

        checkboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                if (!cb.checked) {
                    selectAllCheckbox.checked = false;
                } else {
                    const allChecked = Array.from(checkboxes).every(c => c.checked);
                    selectAllCheckbox.checked = allChecked;
                }
                updateBulkActions();
            });
        });
    }

    // --- Bulk form submission loading overlay ---
    const bulkForm = document.getElementById('bulk-form');
    const bulkOverlay = document.getElementById('bulk-loading-overlay');
    if (bulkForm && bulkOverlay) {
        bulkForm.addEventListener('submit', () => {
            bulkOverlay.classList.add('visible');
        });
        window.addEventListener('load', () => {
            bulkOverlay.classList.remove('visible');
        });
    }

    // --- Loading state for admin forms ---
    document.querySelectorAll('form.editor-form, form[data-loading]').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                submitBtn.classList.add('btn-loading');
                submitBtn.dataset.originalText = submitBtn.textContent;
                const loadingText = this.dataset.loadingText || 'Saving...';
                submitBtn.textContent = loadingText;
            }
        });
    });
}