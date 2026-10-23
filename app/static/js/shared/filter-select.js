const ALLOWED_DAYS = ['7', '14', '30', '90', '180', '365'];

export function isDayCount(value) {
    return ALLOWED_DAYS.includes(value);
}

export function initFilterSelect() {
    document.querySelectorAll('.filter-select').forEach(select => {
        select.addEventListener('change', () => {
            const form = select.form;
            if (!form) return;
            form.classList.add('loading');
            form.submit();
        });
    });

    document.querySelectorAll('select[data-auto-submit]').forEach(select => {
        select.addEventListener('change', () => {
            const value = select.value;
            if (isDayCount(value)) {
                const base = select.dataset.daysUrl || '/admin/analytics';
                window.location.href = base + '?days=' + encodeURIComponent(value);
                return;
            }
            const form = select.closest('form');
            if (!form) return;
            form.classList.add('loading');
            form.submit();
        });
    });

    document.querySelectorAll('select[data-audit-filter]').forEach(select => {
        select.addEventListener('change', () => {
            const form = select.closest('form');
            if (!form) return;
            form.classList.add('loading');
            form.submit();
        });
    });
}

export default initFilterSelect;
