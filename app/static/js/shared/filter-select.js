export function initFilterSelect() {
    document.querySelectorAll('.filter-select').forEach(select => {
        select.addEventListener('change', () => {
            const form = select.form;
            form.classList.add('loading');
            form.submit();
        });
    });

    document.querySelectorAll('[data-auto-submit]').forEach(select => {
        select.addEventListener('change', () => {
            const allowedDays = ['7', '14', '30', '90', '180', '365'];
            if (allowedDays.includes(select.value)) {
                select.closest('form').classList.add('loading');
                window.location.href = '/admin/analytics?days=' + select.value;
            }
        });
    });
}
