import { announce, csrfHeaders } from '../shared/utils.js';
import { initMarkdownToolbar } from './markdown-toolbar.js';
import { initMediaPickers } from './media-picker.js';
import { initEditorHistory } from './editor-history.js';

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

    initMarkdownToolbar();
    initMediaPickers();

    // Collapsible preview, below the editor
    if (togglePreviewBtn && editorSplit) {
        const setPreviewVisible = (visible) => {
            editorSplit.classList.toggle('preview-visible', visible);
            editorSplit.classList.toggle('preview-hidden', !visible);
            const toggleText = togglePreviewBtn.querySelector('.toggle-preview-text');
            if (toggleText) {
                toggleText.textContent = visible ? 'Hide Preview' : 'Show Preview';
            }
            togglePreviewBtn.setAttribute('aria-expanded', String(visible));
        };

        setPreviewVisible(true);

        togglePreviewBtn.addEventListener('click', () => {
            setPreviewVisible(editorSplit.classList.contains('preview-hidden'));
        });
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
                    const tagsInput = document.getElementById('tags');
                    if (titleInput && draft.title) titleInput.value = draft.title;
                    if (summaryInput && draft.summary) summaryInput.value = draft.summary;
                    if (tagsInput && draft.tags) tagsInput.value = draft.tags;
                    bodyTextarea.dispatchEvent(new Event('input', { bubbles: true }));
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
                const tagsInput = document.getElementById('tags');
                const draft = {
                    title: titleInput?.value || '',
                    body: bodyTextarea.value,
                    summary: summaryInput?.value || '',
                    tags: tagsInput?.value || '',
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
        document.getElementById('tags')?.addEventListener('input', saveDraft);

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
        const tagsInput = document.getElementById('tags');
        const initialTitle = titleInput?.value || '';
        const initialSummary = summaryInput?.value || '';
        const initialTags = tagsInput?.value || '';

        function checkDirty() {
            const currentTitle = titleInput?.value || '';
            const currentSummary = summaryInput?.value || '';
            const currentTags = tagsInput?.value || '';
            isDirty = bodyTextarea.value !== initialValue ||
                       currentTitle !== initialTitle ||
                       currentSummary !== initialSummary ||
                       currentTags !== initialTags;
        }

        bodyTextarea.addEventListener('input', checkDirty);
        titleInput?.addEventListener('input', checkDirty);
        summaryInput?.addEventListener('input', checkDirty);
        tagsInput?.addEventListener('input', checkDirty);

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

    const aiButtons = [...document.querySelectorAll('[data-ai-action]')];
    let aiAssistInFlight = false;
    aiButtons.forEach((button) => {
        button.addEventListener('click', async () => {
            if (aiAssistInFlight) return;
            const action = button.dataset.aiAction;
            const result = document.getElementById(`ai-${action}-result`);
            const titleInput = document.getElementById('title');
            const body = bodyTextarea?.value || '';
            const title = titleInput?.value || '';
            const destinationInput = document.getElementById(action === 'summary' ? 'summary' : 'tags');
            const destinationSnapshot = destinationInput?.value || '';
            const sourceSnapshot = { title, body };
            if (!body.trim()) {
                if (result) result.textContent = 'Write some post text first.';
                return;
            }
            aiAssistInFlight = true;
            aiButtons.forEach((item) => {
                item.disabled = true;
                item.setAttribute('aria-busy', 'true');
            });
            if (result) result.textContent = 'Preparing suggestion…';
            try {
                const editorForm = document.querySelector('.editor-form');
                const response = await fetch(editorForm?.dataset.aiAssistUrl || '/admin/ai-assist', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...csrfHeaders(),
                    },
                    body: JSON.stringify({
                        action,
                        title,
                        body,
                        post_id: document.querySelector('.editor-form')?.dataset.postId
                            ? Number(document.querySelector('.editor-form').dataset.postId)
                            : null,
                    }),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Suggestion unavailable.');
                if (action === 'summary' && typeof data.suggestion === 'string' && result) {
                    result.textContent = `Suggestion: ${data.suggestion} `;
                    const applyButton = document.createElement('button');
                    applyButton.type = 'button';
                    applyButton.className = 'btn btn-small btn-ghost';
                    applyButton.textContent = 'Use this summary';
                    applyButton.addEventListener('click', () => {
                        const summaryInput = document.getElementById('summary');
                        if (!summaryInput) return;
                        if (
                            (titleInput?.value || '') !== sourceSnapshot.title ||
                            (bodyTextarea?.value || '') !== sourceSnapshot.body ||
                            summaryInput.value !== destinationSnapshot
                        ) {
                            result.textContent = 'The draft changed while this suggestion was prepared. Request a fresh suggestion.';
                            return;
                        }
                        if (summaryInput.value.trim() && !window.confirm('Replace the current summary with this suggestion?')) return;
                        summaryInput.value = data.suggestion;
                        summaryInput.dispatchEvent(new Event('input', { bubbles: true }));
                        summaryInput.dispatchEvent(new Event('change', { bubbles: true }));
                        summaryInput.focus();
                        result.textContent = 'Suggestion applied. Review it before saving.';
                        announce('AI summary suggestion applied to the editor.');
                    });
                    result.append(applyButton);
                } else if (action === 'tags' && Array.isArray(data.suggestions) && result) {
                    const suggestions = data.suggestions.filter((tag) => typeof tag === 'string');
                    const reused = Array.isArray(data.reused) ? data.reused.join(', ') : '';
                    const fresh = Array.isArray(data.new) ? data.new.join(', ') : '';
                    result.textContent = `Suggestions: ${suggestions.join(', ')}. ` +
                        `${reused ? `Existing tags: ${reused}. ` : ''}${fresh ? `New tag ideas: ${fresh}. ` : ''}`;
                    const applyButton = document.createElement('button');
                    applyButton.type = 'button';
                    applyButton.className = 'btn btn-small btn-ghost';
                    applyButton.textContent = 'Add these tags';
                    applyButton.addEventListener('click', () => {
                        const tagsInput = document.getElementById('tags');
                        if (!tagsInput) return;
                        if (
                            (titleInput?.value || '') !== sourceSnapshot.title ||
                            (bodyTextarea?.value || '') !== sourceSnapshot.body ||
                            tagsInput.value !== destinationSnapshot
                        ) {
                            result.textContent = 'The draft changed while these suggestions were prepared. Request fresh suggestions.';
                            return;
                        }
                        const current = tagsInput.value.split(',').map((tag) => tag.trim()).filter(Boolean);
                        const key = (tag) => tag.toLocaleLowerCase().replace(/\s+/g, '-');
                        const existing = new Set(current.map(key));
                        const additions = suggestions.filter((tag) => !existing.has(key(tag)));
                        if (additions.length) {
                            tagsInput.value = [...current, ...additions].join(', ');
                            tagsInput.dispatchEvent(new Event('input', { bubbles: true }));
                            tagsInput.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        tagsInput.focus();
                        result.textContent = `${additions.length ? `Added: ${additions.join(', ')}. ` : 'No new tags to add. '}Review before saving.`;
                        announce('AI tag suggestions applied to the editor.');
                    });
                    result.append(applyButton);
                }
            } catch (error) {
                if (result) result.textContent = error.message || 'Suggestion unavailable.';
            } finally {
                aiAssistInFlight = false;
                aiButtons.forEach((item) => {
                    item.disabled = false;
                    item.removeAttribute('aria-busy');
                });
            }
        });
    });

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

    // Seeded last so a restored draft is the starting point, not an undo step
    initEditorHistory(bodyTextarea);
}

export default initEditor;
