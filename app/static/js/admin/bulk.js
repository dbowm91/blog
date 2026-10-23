export function initBulk() {
    // --- Bulk Select All ---
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        const getCheckboxes = () => Array.from(document.querySelectorAll('.bulk-checkbox'));

        function updateBulkActions() {
            const bulkActions = document.getElementById('bulk-actions');
            const checkboxes = getCheckboxes();
            const anyChecked = checkboxes.some(cb => cb.checked);

            if (bulkActions) {
                bulkActions.classList.toggle('hidden', !anyChecked);
            }

            const srAnnounce = document.getElementById('sr-announce');
            if (anyChecked && srAnnounce) {
                const form = document.getElementById('bulk-form');
                const checkedCount = checkboxes.filter(cb => cb.checked).length;
                const itemType = form?.dataset.bulkSelect || 'item';
                srAnnounce.textContent = `${checkedCount} ${itemType}${checkedCount === 1 ? '' : 's'} selected`;
            }
        }

        selectAllCheckbox.addEventListener('change', () => {
            getCheckboxes().forEach(cb => {
                cb.checked = selectAllCheckbox.checked;
            });
            updateBulkActions();
        });

        document.addEventListener('change', (e) => {
            const target = e.target;
            if (!target || !target.matches || !target.matches('.bulk-checkbox')) return;
            if (!target.checked) {
                selectAllCheckbox.checked = false;
            } else {
                selectAllCheckbox.checked = getCheckboxes().every(c => c.checked);
            }
            updateBulkActions();
        });

        updateBulkActions();
    }
}

export default initBulk;
