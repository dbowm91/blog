document.addEventListener("DOMContentLoaded", () => {
    // --- Form delete confirmation via data-confirm attribute ---
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', e => {
            if (!confirm(form.dataset.confirm)) e.preventDefault();
        });
    });

    // --- Bulk action confirmation via data-confirm-bulk ---
    document.querySelectorAll('button[data-confirm-bulk]').forEach(btn => {
        btn.addEventListener('click', e => {
            const checked = document.querySelectorAll('.bulk-checkbox:checked');
            if (checked.length === 0) {
                e.preventDefault();
                return;
            }
            if (!confirm(btn.dataset.confirmBulk)) e.preventDefault();
        });
    });

    // --- Element references ---
    const navbar = document.querySelector(".navbar");
    const progressBar = document.getElementById("reading-progress");
    
    // --- Back to top button ---
    const backToTop = document.createElement("button");
    backToTop.className = "back-to-top";
    backToTop.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/></svg>';
    backToTop.setAttribute("aria-label", "Back to top");
    document.body.appendChild(backToTop);
    
    // --- Combined scroll handler with throttling ---
    let scrollTimeout;
    const combinedScrollHandler = () => {
        if (scrollTimeout) return;
        
        scrollTimeout = setTimeout(() => {
            scrollTimeout = null;
            
            if (navbar) {
                navbar.style.padding = window.scrollY > 60 ? "10px 0" : "16px 0";
            }
            
            if (progressBar) {
                const scrollTop = window.scrollY;
                const docHeight = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
                const scrollPercent = (scrollTop / docHeight) * 100;
                progressBar.style.width = `${Math.min(100, scrollPercent)}%`;
            }
            
            if (window.scrollY > 300) {
                backToTop.classList.add("visible");
            } else {
                backToTop.classList.remove("visible");
            }
        }, 10);
    };
    
    window.addEventListener("scroll", combinedScrollHandler, { passive: true });
    
    backToTop.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    // --- Smooth flash dismissal ---
    document.querySelectorAll(".flash").forEach((flash) => {
        flash.style.cursor = "pointer";
        const dismiss = () => {
            flash.style.transition = "opacity 0.3s ease, transform 0.3s ease";
            flash.style.opacity = "0";
            flash.style.transform = "translateY(-8px)";
            setTimeout(() => flash.remove(), 300);
        };
        flash.addEventListener("click", dismiss);
        setTimeout(dismiss, 5000);
    });

    // --- Share button click tracking ---
    const shareBar = document.querySelector(".share-bar");
    if (shareBar) {
        const postId = shareBar.dataset.postId;

        shareBar.querySelectorAll(".share-btn[data-platform]").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                const platform = btn.dataset.platform;

                if (platform === "copy") {
                    e.preventDefault();
                    const shareUrl = shareBar.dataset.shareUrl;
                    const copyToClipboard = (text) => {
                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            return navigator.clipboard.writeText(text);
                        } else {
                            return new Promise((resolve) => {
                                const textarea = document.createElement('textarea');
                                textarea.value = text;
                                document.body.appendChild(textarea);
                                textarea.select();
                                document.execCommand('copy');
                                document.body.removeChild(textarea);
                                resolve();
                            });
                        }
                    };
                    
                    copyToClipboard(shareUrl).then(() => {
                        const original = btn.innerHTML;
                        btn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
                        setTimeout(() => { btn.innerHTML = original; }, 1500);
                    }).catch(() => {
                        console.warn('Failed to copy to clipboard');
                    });
                    return;
                }

                fetch("/api/track-share", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')?.content || "",
                    },
                    body: JSON.stringify({ post_id: parseInt(postId), platform: platform }),
                    keepalive: true,
                }).catch(() => {});
            });
        });
    }

    // --- Code block copy button ---
    document.querySelectorAll('pre[class*="language-"]').forEach((pre) => {
        const button = document.createElement('button');
        button.className = 'copy-code-btn';
        button.textContent = 'Copy';
        button.addEventListener('click', () => {
            const code = pre.querySelector('code');
            if (code) {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(code.textContent).then(() => {
                        button.textContent = 'Copied!';
                        setTimeout(() => { button.textContent = 'Copy'; }, 2000);
                    }).catch(() => {
                        const textarea = document.createElement('textarea');
                        textarea.value = code.textContent;
                        document.body.appendChild(textarea);
                        textarea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textarea);
                        button.textContent = 'Copied!';
                        setTimeout(() => { button.textContent = 'Copy'; }, 2000);
                    });
                } else {
                    const textarea = document.createElement('textarea');
                    textarea.value = code.textContent;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    button.textContent = 'Copied!';
                    setTimeout(() => { button.textContent = 'Copy'; }, 2000);
                }
            }
        });
        pre.appendChild(button);
    });

    // --- Mobile hamburger menu ---
    const mobileMenuToggle = document.createElement('button');
    mobileMenuToggle.className = 'mobile-menu-toggle';
    mobileMenuToggle.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>';
    mobileMenuToggle.setAttribute('aria-label', 'Toggle navigation menu');
    mobileMenuToggle.setAttribute('aria-expanded', 'false');
    
    const navContainer = document.querySelector('.nav-container');
    const navLinks = document.querySelector('.nav-links');
    
    if (navContainer && navLinks) {
        navContainer.appendChild(mobileMenuToggle);
        
        mobileMenuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
            const isOpen = navLinks.classList.contains('open');
            mobileMenuToggle.setAttribute('aria-expanded', isOpen.toString());
            mobileMenuToggle.innerHTML = isOpen 
                ? '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>'
                : '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>';
        });
    }

    // --- Anchor links for headings ---
    const usedIds = new Set();
    document.querySelectorAll('.prose h1, .prose h2, .prose h3, .prose h4').forEach((heading) => {
        if (!heading.id) {
            const text = heading.textContent;
            let id = text.toLowerCase()
                .replace(/[^\w\s-]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-')
                .trim();
            
            if (!id) {
                const headingType = heading.tagName.toLowerCase();
                let counter = 1;
                id = `${headingType}-${counter}`;
                while (usedIds.has(id)) {
                    counter++;
                    id = `${headingType}-${counter}`;
                }
            } else {
                let finalId = id;
                let counter = 1;
                while (usedIds.has(finalId)) {
                    finalId = `${id}-${counter}`;
                    counter++;
                }
                id = finalId;
            }
            usedIds.add(id);
            heading.id = id;
        } else {
            usedIds.add(heading.id);
        }
        
        const wrapper = document.createElement('span');
        wrapper.className = 'heading-anchor';
        
        const anchor = document.createElement('a');
        anchor.className = 'anchor-link';
        anchor.href = `#${heading.id}`;
        anchor.innerHTML = '#';
        anchor.setAttribute('aria-label', 'Link to this section');
        
        while (heading.firstChild) {
            wrapper.appendChild(heading.firstChild);
        }
        
        heading.appendChild(wrapper);
        heading.appendChild(anchor);
    });

    // --- Lazy loading for images ---
    if (!('loading' in HTMLImageElement.prototype)) {
        document.querySelectorAll('img:not([loading])').forEach((img) => {
            const rect = img.getBoundingClientRect();
            if (rect.top > window.innerHeight * 1.5) {
                img.setAttribute('loading', 'lazy');
            }
        });
    }

    // --- Item 8: Live Markdown Preview ---
    const bodyTextarea = document.getElementById('body');
    const previewDiv = document.getElementById('markdown-preview');
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    if (bodyTextarea && previewDiv) {
        let debounceTimer;
        const updatePreview = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const text = bodyTextarea.value;
                if (!text.trim()) {
                    previewDiv.innerHTML = '<p class="empty-state">Live preview will appear here...</p>';
                    return;
                }
                fetch("/admin/preview-markdown", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRF-Token": csrfToken,
                    },
                    body: JSON.stringify({ text: text }),
                })
                .then(r => r.json())
                .then(data => {
                    if (data.html) {
                        previewDiv.innerHTML = data.html;
                    }
                })
                .catch(() => {});
            }, 300);
        };

        bodyTextarea.addEventListener('input', updatePreview);
        // Trigger initial preview if there's content
        if (bodyTextarea.value.trim()) {
            updatePreview();
        }
    }

    // --- Item 9: Draft Autosave ---
    if (bodyTextarea) {
        const postId = window.location.pathname.match(/\/edit\/(\d+)/)?.[1] || 'new';
        const draftKey = `draft-${postId}`;
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
        const saveDraft = () => {
            clearTimeout(autosaveTimer);
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
    }

    // --- Item 10: Dark/Light Mode Toggle ---
    const themeToggle = document.createElement('button');
    themeToggle.className = 'theme-toggle';
    themeToggle.setAttribute('aria-label', 'Toggle theme');

    const setThemeIcon = (isDark) => {
        themeToggle.innerHTML = isDark
            ? '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/></svg>'
            : '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>';
    };

    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = savedTheme ? savedTheme === 'dark' : prefersDark;

    if (!isDark) {
        document.documentElement.setAttribute('data-theme', 'light');
    }
    setThemeIcon(isDark);

    themeToggle.addEventListener('click', () => {
        const currentlyDark = !document.documentElement.hasAttribute('data-theme') || document.documentElement.getAttribute('data-theme') === 'dark';
        if (currentlyDark) {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
            setThemeIcon(false);
        } else {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'dark');
            setThemeIcon(true);
        }
    });

    // Insert theme toggle into navbar
    const navLinksEl = document.querySelector('.nav-links');
    if (navLinksEl) {
        const li = document.createElement('span');
        li.appendChild(themeToggle);
        navLinksEl.prepend(li);
    }

    // --- Item 14: Bulk Select All ---
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', () => {
            document.querySelectorAll('.bulk-checkbox').forEach(cb => {
                cb.checked = selectAllCheckbox.checked;
            });
        });
    }

    // --- Media Copy URL ---
    document.querySelectorAll('.media-copy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const url = btn.dataset.url;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(() => {
                    btn.textContent = 'Copied!';
                    setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
                }).catch(() => {});
            }
        });
    });
});
