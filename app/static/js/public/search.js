import { debounce } from '../shared/utils.js';

export function initSearch() {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;

    const searchForm = searchInput.closest('form');
    const suggestionsContainer = document.getElementById('search-suggestions');
    const clearBtn = searchInput.parentElement.querySelector('.search-clear');

    if (!suggestionsContainer) {
        createSuggestionsContainer(searchInput);
    }

    let currentRequest = null;

    const updateClearButton = () => {
        if (clearBtn) {
            clearBtn.style.display = searchInput.value ? 'block' : 'none';
        }
    };

    const clearSearch = () => {
        searchInput.value = '';
        updateClearButton();
        hideSuggestions();
        searchInput.focus();
    };

    if (clearBtn) {
        clearBtn.addEventListener('click', clearSearch);
    }

    searchInput.addEventListener('input', updateClearButton);
    updateClearButton();

    const fetchSuggestions = debounce(async (query) => {
        if (!query || query.length < 2) {
            hideSuggestions();
            searchForm.classList.remove('loading');
            return;
        }

        if (currentRequest) {
            currentRequest.abort();
        }

        searchForm.classList.add('loading');
        currentRequest = new AbortController();

        try {
            const response = await fetch(`/search/suggest?q=${encodeURIComponent(query)}`, {
                signal: currentRequest.signal,
                headers: {
                    'Accept': 'application/json',
                },
            });

            if (!response.ok) return;

            const data = await response.json();
            displaySuggestions(data.suggestions || []);
        } catch (err) {
            if (err.name !== 'AbortError') {
                console.warn('Search suggestions error:', err);
            }
        } finally {
            searchForm.classList.remove('loading');
        }
    }, 250);

    searchInput.addEventListener('input', (e) => {
        fetchSuggestions(e.target.value.trim());
    });

    searchInput.addEventListener('focus', () => {
        const query = searchInput.value.trim();
        if (query.length >= 2) {
            fetchSuggestions(query);
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-wrapper')) {
            hideSuggestions();
        }
    });

    searchInput.addEventListener('keydown', (e) => {
        const suggestions = document.querySelector('.search-suggestions');
        if (!suggestions) return;

        const items = suggestions.querySelectorAll('.suggestion-item');
        const active = suggestions.querySelector('.suggestion-item.active');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (!active) {
                items[0]?.classList.add('active');
            } else {
                const idx = Array.from(items).indexOf(active);
                items[idx]?.classList.remove('active');
                items[idx + 1]?.classList.add('active');
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (active) {
                const idx = Array.from(items).indexOf(active);
                items[idx]?.classList.remove('active');
                items[idx - 1]?.classList.add('active');
            }
        } else if (e.key === 'Enter' && active) {
            e.preventDefault();
            const link = active.querySelector('a');
            if (link) {
                window.location.href = link.href;
            }
        } else if (e.key === 'Escape') {
            hideSuggestions();
        }
    });
}

function createSuggestionsContainer(searchInput) {
    const wrapper = document.createElement('div');
    wrapper.className = 'search-wrapper';

    const container = document.createElement('div');
    container.id = 'search-suggestions';
    container.className = 'search-suggestions';
    container.setAttribute('role', 'listbox');
    container.setAttribute('aria-label', 'Search suggestions');

    searchInput.parentNode.insertBefore(wrapper, searchInput);
    wrapper.appendChild(searchInput);
    wrapper.appendChild(container);
}

function displaySuggestions(posts) {
    let container = document.getElementById('search-suggestions');
    if (!container) {
        const searchInput = document.getElementById('search-input');
        if (!searchInput) return;
        createSuggestionsContainer(searchInput);
        container = document.getElementById('search-suggestions');
    }

    if (!posts || posts.length === 0) {
        hideSuggestions();
        return;
    }

    container.innerHTML = posts.map(post => `
        <div class="suggestion-item" role="option">
            <a href="/post/${post.slug}">
                <span class="suggestion-title">${escapeHtml(post.title)}</span>
                ${post.summary ? `<span class="suggestion-summary">${escapeHtml(post.summary.substring(0, 80))}...</span>` : ''}
            </a>
        </div>
    `).join('');

    container.style.display = 'block';

    container.style.display = 'block';
}

function hideSuggestions() {
    const container = document.getElementById('search-suggestions');
    if (container) {
        container.style.display = 'none';
        container.innerHTML = '';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export default initSearch;
