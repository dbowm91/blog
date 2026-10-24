const MAX_ENTRIES = 200;
const COALESCE_MS = 600;

export function createHistory({ read, write, max = MAX_ENTRIES, coalesceMs = COALESCE_MS }) {
    const stack = [];
    let index = -1;
    let lastPushAt = 0;
    let applying = false;
    let structural = false;

    function push(entry) {
        if (index < stack.length - 1) {
            stack.length = index + 1;
        }
        stack.push(entry);
        if (stack.length > max) {
            stack.shift();
        }
        index = stack.length - 1;
    }

    function apply(target) {
        const entry = stack[target];
        applying = true;
        write(entry);
        applying = false;
        lastPushAt = 0;
    }

    function record(force = false) {
        if (applying) return;

        const snapshot = read();
        const entry = index >= 0 ? stack[index] : null;

        if (entry && entry.value === snapshot.value) {
            entry.start = snapshot.start;
            entry.end = snapshot.end;
            return;
        }

        const now = Date.now();
        if (!force && entry && now - lastPushAt < coalesceMs) {
            entry.value = snapshot.value;
            entry.start = snapshot.start;
            entry.end = snapshot.end;
            lastPushAt = now;
            return;
        }

        push(snapshot);
        lastPushAt = now;
    }

    function undo() {
        if (index <= 0) return false;
        index -= 1;
        apply(index);
        return true;
    }

    function redo() {
        if (index < 0 || index >= stack.length - 1) return false;
        index += 1;
        apply(index);
        return true;
    }

    return {
        seed() {
            push(read());
            lastPushAt = 0;
        },
        record,
        undo,
        redo,
        canUndo: () => index > 0,
        canRedo: () => index >= 0 && index < stack.length - 1,
        markStructural() {
            structural = true;
        },
        takeStructural() {
            const flagged = structural;
            structural = false;
            return flagged;
        },
    };
}

export function initEditorHistory(textarea) {
    if (!textarea) return null;

    const toolbar = document.querySelector('.editor-toolbar');
    const undoButton = toolbar ? toolbar.querySelector('[data-history-action="undo"]') : null;
    const redoButton = toolbar ? toolbar.querySelector('[data-history-action="redo"]') : null;

    const history = createHistory({
        read: () => ({
            value: textarea.value,
            start: textarea.selectionStart,
            end: textarea.selectionEnd,
        }),
        write: (entry) => {
            textarea.value = entry.value;
            textarea.setSelectionRange(entry.start, entry.end);
            textarea.focus();
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        },
    });

    function syncButtons() {
        if (undoButton) undoButton.disabled = !history.canUndo();
        if (redoButton) redoButton.disabled = !history.canRedo();
    }

    history.seed();
    syncButtons();

    textarea.addEventListener('editor:structural', () => {
        history.markStructural();
    });

    textarea.addEventListener('input', () => {
        history.record(history.takeStructural());
        syncButtons();
    });

    textarea.addEventListener('keydown', (event) => {
        if (!event.metaKey && !event.ctrlKey) return;

        const key = event.key.toLowerCase();
        if (key === 'z' && !event.shiftKey) {
            event.preventDefault();
            history.undo();
            syncButtons();
        } else if ((key === 'z' && event.shiftKey) || key === 'y') {
            event.preventDefault();
            history.redo();
            syncButtons();
        }
    });

    if (toolbar) {
        toolbar.addEventListener('mousedown', (event) => {
            if (event.target.closest('[data-history-action]')) {
                event.preventDefault();
            }
        });
    }

    if (undoButton) {
        undoButton.addEventListener('click', () => {
            history.undo();
            syncButtons();
        });
    }

    if (redoButton) {
        redoButton.addEventListener('click', () => {
            history.redo();
            syncButtons();
        });
    }

    return history;
}
