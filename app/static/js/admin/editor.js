import { announce, csrfHeaders } from '../shared/utils.js';

export function deriveDraftKey(pathname) {
    const editorType = /\/admin\/pages\//.test(pathname) ? 'page' : 'post';
    const idMatch = pathname.match(/\/edit\/(\d+)/);
    return idMatch ? `draft-${editorType}-${idMatch[1]}` : `draft-${editorType}-new`;
}

export function initEditor() {
    const bodyTextarea = document.getElementById('body');
    const previewDiv = document.getElementById('markdown-preview');
    const editorSplit = document.getElementById('editor-split');
    const togglePreviewBtn = document.getElementById('toggle-preview-btn');

    // Mobile preview toggle
    if (togglePreviewBtn && editorSplit) {
        const isMobile = window.matchMedia('(max-width: 768px)').matches;

        const setPreviewVisible = (visible) => {
            editorSplit.classList.toggle('preview-visible', visible);
            editorSplit.classList.toggle('preview-hidden', !visible);
            const toggleText = togglePreviewBtn.querySelector('.toggle-preview-text');
            if (toggleText) {
                toggleText.textContent = visible ? 'Hide Preview' : 'Show Preview';
            }
            togglePreviewBtn.setAttribute('aria-expanded', String(visible));
        };

        setPreviewVisible(!isMobile);

        togglePreviewBtn.addEventListener('click', () => {
            setPreviewVisible(!editorSplit.classList.contains('preview-visible'));
        });

        const syncPreviewState = new MutationObserver(() => {
            const visible = !editorSplit.classList.contains('preview-hidden');
            if (editorSplit.classList.contains('preview-visible') !== visible) {
                setPreviewVisible(visible);
            }
        });
        syncPreviewState.observe(editorSplit, { attributes: true, attributeFilter: ['class'] });
    }

    if (bodyTextarea && previewDiv) {
        let serverRequest = null;
        let previewTimeout = null;

        const fetchServerPreview = (text) => {
            if (serverRequest) {
                serverRequest.abortController.abort();
            }
            const abortController = new AbortController();
            serverRequest = { abortController };

            previewDiv.classList.add('preview-loading');
            fetch("/admin/preview-markdown", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...csrfHeaders(),
                },
                body: JSON.stringify({ text: text }),
                signal: abortController.signal,
            })
            .then(r => r.json())
            .then(data => {
                previewDiv.classList.remove('preview-loading');
                if (data && data.html) {
                    previewDiv.innerHTML = data.html;
                }
            })
            .catch((err) => {
                previewDiv.classList.remove('preview-loading');
                if (err.name !== 'AbortError') {
                    previewDiv.innerHTML = '<p class="form-error">Preview unavailable</p>';
                }
            });
        };

        const debouncedFetchServerPreview = (text) => {
            clearTimeout(previewTimeout);
            previewTimeout = setTimeout(() => fetchServerPreview(text), 300);
        };

        const updatePreview = () => {
            const text = bodyTextarea.value;
            if (!text.trim()) {
                previewDiv.innerHTML = '<p class="empty-state">Live preview will appear here...</p>';
                return;
            }
            debouncedFetchServerPreview(text);
        };

        bodyTextarea.addEventListener('input', updatePreview);
        if (bodyTextarea.value.trim()) {
            updatePreview();
        }
    }

    // --- Draft Autosave ---
    if (bodyTextarea) {
        const draftKey = deriveDraftKey(window.location.pathname);
        let autosaveTimer;

        // Restore draft on load
        const savedDraft = localStorage.getItem(draftKey);
        if (savedDraft && !bodyTextarea.value) {
            try {
                const draft = JSON.parse(savedDraft);
                if (draft.body && confirm('Restore unsaved changes from your last session?')) {
                    bodyTextarea.value = draft.body;
                    const titleInput = document.getElementById('title');
                    const summaryInput = document.getElementById('summary');
                    if (titleInput && draft.title) titleInput.value = draft.title;
                    if (summaryInput && draft.summary) summaryInput.value = draft.summary;
                }
            } catch (e) {
                localStorage.removeItem(draftKey);
            }
        }

        // Save draft on input (throttled every 5s)
        const autosaveStatus = document.getElementById('autosave-status');
        const saveDraft = () => {
            clearTimeout(autosaveTimer);
            if (autosaveStatus) {
                autosaveStatus.textContent = 'Saving...';
                autosaveStatus.style.opacity = '1';
            }
            autosaveTimer = setTimeout(() => {
                const titleInput = document.getElementById('title');
                const summaryInput = document.getElementById('summary');
                const draft = {
                    title: titleInput?.value || '',
                    body: bodyTextarea.value,
                    summary: summaryInput?.value || '',
                    timestamp: Date.now(),
                };
                try {
                    localStorage.setItem(draftKey, JSON.stringify(draft));
                    if (autosaveStatus) {
                        autosaveStatus.textContent = 'Draft saved';
                        announce('Draft saved');
                        setTimeout(() => { autosaveStatus.style.opacity = '0'; }, 2000);
                    }
                } catch (e) {}
            }, 5000);
        };

        bodyTextarea.addEventListener('input', saveDraft);
        document.getElementById('title')?.addEventListener('input', saveDraft);
        document.getElementById('summary')?.addEventListener('input', saveDraft);

        // Clear draft on successful submit
        const editorForm = document.querySelector('.editor-form');
        if (editorForm) {
            editorForm.addEventListener('submit', () => {
                localStorage.removeItem(draftKey);
            });
        }

        // --- Unsaved Changes Warning ---
        let isDirty = false;
        const initialValue = bodyTextarea.value;
        const titleInput = document.getElementById('title');
        const summaryInput = document.getElementById('summary');
        const initialTitle = titleInput?.value || '';
        const initialSummary = summaryInput?.value || '';

        function checkDirty() {
            const currentTitle = titleInput?.value || '';
            const currentSummary = summaryInput?.value || '';
            isDirty = bodyTextarea.value !== initialValue ||
                       currentTitle !== initialTitle ||
                       currentSummary !== initialSummary;
        }

        bodyTextarea.addEventListener('input', checkDirty);
        titleInput?.addEventListener('input', checkDirty);
        summaryInput?.addEventListener('input', checkDirty);

        window.addEventListener('beforeunload', (e) => {
            if (isDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // Clear warning on form submit
        if (editorForm) {
            editorForm.addEventListener('submit', () => {
                isDirty = false;
            });
        }
    }

    // --- Word/Character Count in Editor ---
    const wordCountEl = document.getElementById('word-count');
    const charCountEl = document.getElementById('char-count');

    if (bodyTextarea && wordCountEl && charCountEl) {
        let countTimer;
        const updateCounts = () => {
            clearTimeout(countTimer);
            countTimer = setTimeout(() => {
                const text = bodyTextarea.value;
                const charCount = text.length;
                const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
                wordCountEl.textContent = `${wordCount} word${wordCount !== 1 ? 's' : ''}`;
                charCountEl.textContent = `${charCount} character${charCount !== 1 ? 's' : ''}`;
            }, 500);
        };

        bodyTextarea.addEventListener('input', updateCounts);
        updateCounts();
    }
}

export default initEditor;
