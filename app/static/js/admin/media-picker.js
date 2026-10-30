import { announce, csrfHeaders } from '../shared/utils.js';

const MEDIA_API = '/admin/media/items';
const UPLOAD_API = '/admin/media/upload';
const IMAGE_ACCEPT = 'image/png,image/jpeg,image/gif,image/webp';
const VIDEO_ACCEPT = 'video/mp4,video/webm,.mp4,.webm';

export function escapeMarkdownLabel(value) {
    return String(value || '').replace(/[\\[\]]/g, '\\$&');
}

function safeUrl(value) {
    if (typeof value !== 'string' || !value.trim()) return null;
    try {
        const parsed = new URL(value, window.location.origin);
        if (!['http:', 'https:'].includes(parsed.protocol)) return null;
        if (parsed.username || parsed.password) return null;
        if (parsed.origin !== window.location.origin && parsed.protocol !== 'https:') return null;
        return value;
    } catch {
        return null;
    }
}

function escapeHtmlAttribute(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function markdownUrl(value) {
    return `<${value.replace(/[<>]/g, (char) => encodeURIComponent(char))}>`;
}

export function formatMediaMarkdown(item, mode, selectedText = '') {
    if (!item || typeof item !== 'object') return null;
    const displayName = String(item.display_name || item.name || '').trim();
    if (!displayName) return null;
    const label = escapeMarkdownLabel(selectedText.trim().replace(/\s+/g, ' ') || displayName);

    if (mode === 'attachment') {
        const url = safeUrl(item.download_url);
        return url ? `[${label}](${markdownUrl(url)})` : null;
    }

    if (item.category === 'image') {
        const url = safeUrl(item.url);
        return url ? `![${label}](${markdownUrl(url)})` : null;
    }

    if (item.category === 'video') {
        const url = safeUrl(item.url);
        if (!url) return null;
        const mime = item.mime_type;
        if (!['video/mp4', 'video/webm'].includes(mime)) return null;
        return `<video controls>\n  <source src="${escapeHtmlAttribute(url)}" type="${mime}">\n</video>`;
    }

    return null;
}

export function replaceMarkdownSelection(textarea, markup, selection) {
    if (!textarea || typeof markup !== 'string') return false;
    const value = textarea.value;
    const start = Math.max(0, Math.min(selection?.start ?? textarea.selectionStart, value.length));
    const end = Math.max(start, Math.min(selection?.end ?? textarea.selectionEnd, value.length));
    const isBlock = markup.startsWith('<video');
    const before = value.slice(0, start);
    const after = value.slice(end);
    const leading = isBlock && before && !before.endsWith('\n') ? '\n\n' : '';
    const trailing = isBlock && after && !after.startsWith('\n') ? '\n\n' : '';
    const insertion = `${leading}${markup}${trailing}`;

    textarea.dispatchEvent(new CustomEvent('editor:structural', { bubbles: true }));
    textarea.value = before + insertion + after;
    const cursor = before.length + insertion.length;
    textarea.focus();
    textarea.setSelectionRange(cursor, cursor);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
}

export function initMediaPickers() {
    const textarea = document.getElementById('body');
    const dialog = document.getElementById('editor-media-picker');
    if (!textarea || !dialog) return;

    const title = dialog.querySelector('[data-picker-title]');
    const category = dialog.querySelector('[data-picker-category]');
    const search = dialog.querySelector('[data-picker-search]');
    const uploadCategory = dialog.querySelector('[data-upload-category]');
    const uploadCategoryGroup = dialog.querySelector('[data-upload-category-group]');
    const fileInput = dialog.querySelector('[data-picker-file]');
    const uploadButton = dialog.querySelector('[data-picker-upload]');
    const list = dialog.querySelector('[data-picker-items]');
    const status = dialog.querySelector('[data-picker-status]');
    const empty = dialog.querySelector('[data-picker-empty]');
    if (!title || !category || !search || !uploadCategory || !uploadCategoryGroup || !fileInput || !uploadButton || !list || !status || !empty) return;

    let mode = 'media';
    let activeTrigger = null;
    let savedSelection = null;
    let requestSequence = 0;
    let searchTimer = null;
    let busy = false;
    const itemByButton = new WeakMap();

    const setStatus = (message, isError = false) => {
        status.textContent = message;
        status.classList.toggle('is-error', isError);
        if (message) announce(message);
    };

    const updateUploadControls = () => {
        const isMedia = mode === 'media';
        uploadCategoryGroup.hidden = !isMedia;
        fileInput.accept = !isMedia || uploadCategory.value === 'other'
            ? ''
            : uploadCategory.value === 'image' ? IMAGE_ACCEPT : VIDEO_ACCEPT;
    };

    const renderItems = (items) => {
        list.replaceChildren();
        const filtered = items.filter((item) => {
            if (mode === 'media') return ['image', 'video'].includes(item.category);
            return true;
        });
        empty.hidden = filtered.length > 0;
        if (!filtered.length) return;

        filtered.forEach((item) => {
            const url = mode === 'attachment' ? item.download_url : item.url;
            const canInsert = Boolean(formatMediaMarkdown(item, mode));
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'editor-media-item';
            button.disabled = !canInsert || busy;
            itemByButton.set(button, item);
            button.setAttribute(
                'aria-label',
                canInsert
                    ? `${item.category}: ${item.display_name || item.name}`
                    : `${item.category}: ${item.display_name || item.name}; no safe download is available`
            );
            button.dataset.name = String(item.name || '');

            const kind = document.createElement('span');
            kind.className = 'editor-media-kind';
            kind.textContent = item.category;
            const name = document.createElement('span');
            name.className = 'editor-media-name';
            name.textContent = String(item.display_name || item.name || 'Unnamed file');
            const detail = document.createElement('span');
            detail.className = 'editor-media-detail';
            detail.textContent = canInsert
                ? `${Math.max(1, Math.round(Number(item.size || 0) / 1024))} KB`
                : 'No safe download link';
            button.append(kind, name, detail);
            if (canInsert) button.dataset.url = String(url || '');
            list.append(button);
        });
    };

    const loadItems = async () => {
        const sequence = ++requestSequence;
        const requestedCategory = category.value;
        const params = new URLSearchParams({ category: requestedCategory, search: search.value.trim() });
        setStatus('Loading files…');
        list.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(`${MEDIA_API}?${params.toString()}`, {
                headers: { Accept: 'application/json' },
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Could not load files.');
            if (sequence !== requestSequence) return;
            renderItems(Array.isArray(data.items) ? data.items : []);
            setStatus(`${list.children.length} file${list.children.length === 1 ? '' : 's'} available.`);
        } catch (error) {
            if (sequence !== requestSequence) return;
            list.replaceChildren();
            empty.hidden = false;
            empty.textContent = 'Files could not be loaded. Try again.';
            setStatus(error.message || 'Could not load files.', true);
        } finally {
            if (sequence === requestSequence) list.removeAttribute('aria-busy');
        }
    };

    const chooseUploadCategory = () => mode === 'attachment' ? 'other' : uploadCategory.value;

    const finishWithItem = (item) => {
        if (!dialog.open) return;
        const selectedText = savedSelection
            ? savedSelection.value.slice(savedSelection.start, savedSelection.end)
            : '';
        const markup = formatMediaMarkdown(item, mode, selectedText);
        if (!markup) {
            setStatus('This file cannot be inserted safely in this picker.', true);
            return;
        }
        if (savedSelection && textarea.value !== savedSelection.value) {
            setStatus('The editor changed while the picker was open. Close it and try again.', true);
            return;
        }
        dialog.close();
        replaceMarkdownSelection(textarea, markup, savedSelection);
        setStatus('');
    };

    const setBusy = (value) => {
        busy = value;
        uploadButton.disabled = value;
        category.disabled = value;
        search.disabled = value;
        uploadCategory.disabled = value;
        dialog.querySelectorAll('.editor-media-item').forEach((item) => {
            item.disabled = value || item.dataset.url === undefined;
        });
    };

    const uploadFile = async (file) => {
        if (!file) return;
        const form = new FormData();
        form.append('file', file);
        form.append('category', chooseUploadCategory());
        setBusy(true);
        setStatus(`Uploading ${file.name}…`);
        try {
            const response = await fetch(UPLOAD_API, {
                method: 'POST',
                headers: {
                    ...csrfHeaders(),
                    Accept: 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: form,
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Upload failed.');
            if (!data.item || typeof data.item !== 'object') throw new Error('Upload returned no file.');
            const item = {
                ...data.item,
                download_url: data.item.download_url || (data.item.category === 'other' ? data.item.url : null),
                size: file.size,
            };
            finishWithItem(item);
        } catch (error) {
            setStatus(error.message || 'Upload failed. Your draft was not changed.', true);
        } finally {
            setBusy(false);
            fileInput.value = '';
        }
    };

    document.querySelectorAll('[data-media-picker-trigger]').forEach((trigger) => {
        trigger.addEventListener('pointerdown', (event) => {
            if (event.button === 0) event.preventDefault();
        });
        trigger.addEventListener('click', () => {
            if (dialog.open || busy) return;
            mode = trigger.dataset.mediaPickerTrigger === 'attachment' ? 'attachment' : 'media';
            activeTrigger = trigger;
            activeTrigger.setAttribute('aria-expanded', 'true');
            savedSelection = {
                value: textarea.value,
                start: textarea.selectionStart,
                end: textarea.selectionEnd,
            };
            title.textContent = mode === 'attachment' ? 'Choose an attachment' : 'Choose inline media';
            category.value = mode === 'attachment' ? 'other' : 'all';
            category.querySelector('option[value="other"]').hidden = mode === 'media';
            uploadCategory.value = 'image';
            search.value = '';
            empty.textContent = 'No matching files.';
            updateUploadControls();
            dialog.showModal();
            search.focus();
            loadItems();
        });
    });

    dialog.querySelectorAll('[data-picker-close]').forEach((button) => {
        button.addEventListener('click', () => dialog.close());
    });
    dialog.addEventListener('close', () => {
        if (activeTrigger) {
            activeTrigger.setAttribute('aria-expanded', 'false');
            activeTrigger.focus();
        }
    });
    category.addEventListener('change', loadItems);
    search.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(loadItems, 180);
    });
    uploadCategory.addEventListener('change', updateUploadControls);
    uploadButton.addEventListener('click', () => {
        fileInput.value = '';
        fileInput.click();
    });
    fileInput.addEventListener('change', () => uploadFile(fileInput.files?.[0]));
    list.addEventListener('click', (event) => {
        const button = event.target.closest('.editor-media-item');
        if (!button || button.disabled) return;
        const item = itemByButton.get(button);
        if (item) finishWithItem(item);
    });

}

export default initMediaPickers;
