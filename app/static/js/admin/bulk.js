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
}

export default initBulk;
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

    // --- Keyboard shortcuts for bulk operations ---
    if (bulkForm) {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'a' && !e.shiftKey) {
                    const target = e.target;
                    if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA' && !target.isContentEditable) {
                        const selectAll = document.getElementById('select-all');
                        if (selectAll && !selectAll.checked) {
                            selectAll.checked = true;
                            selectAll.dispatchEvent(new Event('change'));
                            e.preventDefault();
                        }
                    }
                }
            }
        });
    }

    // --- Toast notifications for bulk action results ---
    if (bulkForm) {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('bulk_success')) {
            const count = urlParams.get('bulk_success');
            import('../shared/toast.js').then(({ showToast }) => {
                showToast(`Successfully processed ${count} item${count === '1' ? '' : 's'}.`, 'success');
            }).catch(() => {});
            window.history.replaceState({}, '', window.location.pathname);
        }
        if (urlParams.has('bulk_error')) {
            const error = urlParams.get('bulk_error');
            import('../shared/toast.js').then(({ showToast }) => {
                showToast(`Error: ${error}`, 'error');
            }).catch(() => {});
            window.history.replaceState({}, '', window.location.pathname);
        }
    }
}