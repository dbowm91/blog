document.documentElement.classList.add('js');
document.addEventListener("DOMContentLoaded", () => {
    // --- Screen reader announcement helper ---
    function announce(message) {
        const el = document.getElementById('sr-announce');
        if (el) {
            el.textContent = '';
            setTimeout(() => { el.textContent = message; }, 50);
        }
    }

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
                navbar.classList.toggle('navbar-shrunk', window.scrollY > 60);
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
                        }
                        throw new Error('Clipboard API not available');
                    };
                    
                    copyToClipboard(shareUrl).then(() => {
                        const original = btn.innerHTML;
                        btn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
                        setTimeout(() => { btn.innerHTML = original; }, 1500);
                    }).catch(() => {
                        btn.textContent = 'Failed';
                        setTimeout(() => { btn.innerHTML = original; }, 1500);
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
                        button.textContent = 'Failed';
                        setTimeout(() => { button.textContent = 'Copy'; }, 2000);
                    });
                } else {
                    button.textContent = 'Failed';
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

        // Close menu on outside click
        document.addEventListener('click', (e) => {
            const hamburger = document.querySelector('.mobile-menu-toggle');
            const nav = document.querySelector('.nav-links');
            if (hamburger && nav && !hamburger.contains(e.target) && !nav.contains(e.target)) {
                hamburger.setAttribute('aria-expanded', 'false');
                nav.classList.remove('open');
            }
        });

        // Close menu on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const hamburger = document.querySelector('.mobile-menu-toggle');
                const nav = document.querySelector('.nav-links');
                if (hamburger && nav) {
                    hamburger.setAttribute('aria-expanded', 'false');
                    nav.classList.remove('open');
                }
            }
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
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const fullUrl = window.location.origin + window.location.pathname + anchor.href;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(fullUrl).then(() => {
                    const toast = document.createElement('div');
                    toast.className = 'toast';
                    toast.textContent = 'Link copied!';
                    document.body.appendChild(toast);
                    requestAnimationFrame(() => toast.classList.add('visible'));
                    setTimeout(() => {
                        toast.classList.remove('visible');
                        setTimeout(() => toast.remove(), 300);
                    }, 2000);
                });
            }
        });
        
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
            if (rect.top > window.innerHeight * 3) {
                img.setAttribute('loading', 'lazy');
            }
        });
    }

    // Fade in lazy images on load
    document.querySelectorAll('img[loading="lazy"]').forEach((img) => {
        if (img.complete) {
            img.classList.add('loaded');
        } else {
            img.addEventListener('load', () => img.classList.add('loaded'));
            img.addEventListener('error', () => img.classList.add('loaded'));
        }
    });

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
                previewDiv.classList.add('preview-loading');
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
                    previewDiv.classList.remove('preview-loading');
                    if (data.html) {
                        previewDiv.innerHTML = data.html;
                    }
                })
                .catch(() => {
                    previewDiv.classList.remove('preview-loading');
                    previewDiv.innerHTML = '<p class="form-error">Preview unavailable</p>';
                });
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
        const wrapper = document.createElement('span');
        wrapper.appendChild(themeToggle);
        navLinksEl.prepend(wrapper);
    }

    // Listen for OS theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        const stored = localStorage.getItem('theme');
        if (!stored) {
            document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
            setThemeIcon(e.matches);
        }
    });

    // --- Item 14: Bulk Select All ---
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', () => {
            document.querySelectorAll('.bulk-checkbox').forEach(cb => {
                cb.checked = selectAllCheckbox.checked;
            });
        });
    }

    // --- 5B.1: Loading state for admin forms ---
    document.querySelectorAll('form.editor-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                submitBtn.dataset.originalText = submitBtn.textContent;
                submitBtn.textContent = 'Saving...';
            }
        });
    });

    // --- Media Copy URL ---
    document.querySelectorAll('.media-copy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const url = btn.dataset.url;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(() => {
                    btn.textContent = 'Copied!';
                    setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
                }).catch(() => {
                    btn.textContent = 'Failed';
                    setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
                });
            } else {
                btn.textContent = 'Failed';
                setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
            }
        });
    });

    // --- Dashboard filter select auto-submit ---
    document.querySelectorAll('.filter-select').forEach(select => {
        select.addEventListener('change', () => {
            select.form.submit();
        });
    });

    // --- Analytics select auto-submit ---
    document.querySelectorAll('[data-auto-submit]').forEach(select => {
        select.addEventListener('change', () => {
            window.location.href = '/admin/analytics?days=' + select.value;
        });
    });

    // --- Vim-style keyboard navigation (admin only) ---
    if (document.body.classList.contains('admin-body')) {
    let vimKey = null;
    let vimTimer = null;

    document.addEventListener('keydown', (e) => {
        // Clear vim state on any non-g key (unless modifier is held)
        if (vimKey && !e.ctrlKey && !e.metaKey && !e.altKey && e.key.length === 1) {
            if (vimKey === 'g' && e.key !== 'd' && e.key !== 'p' && e.key !== 's' && e.key !== 't') {
                vimKey = null;
                clearTimeout(vimTimer);
            }
        }

        // g key: prime for vim-style nav
        if (!vimKey && e.key === 'g' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const tag = e.target.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA' && !e.target.isContentEditable) {
                vimKey = 'g';
                clearTimeout(vimTimer);
                vimTimer = setTimeout(() => { vimKey = null; }, 500);
            }
        }

        // gd = Dashboard, gp = Posts, gs = Subscribers, gt = Tags
        if (vimKey === 'g') {
            const routes = { d: '/admin/', p: '/admin/posts', s: '/admin/subscribers', t: '/admin/tags' };
            if (routes[e.key]) {
                window.location.href = routes[e.key];
                vimKey = null;
                clearTimeout(vimTimer);
            }
        }
    });

    // --- Keyboard shortcuts for admin ---
    document.addEventListener('keydown', (e) => {
        // Ignore if user is typing in an input/textarea
        const tag = e.target.tagName;
        const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable;
        const mod = e.ctrlKey || e.metaKey;

        // Ctrl/Cmd+S: Save draft
        if (mod && e.key === 's' && !isInput) {
            const saveBtn = document.querySelector('button[name="action"][value="save"]');
            if (saveBtn) {
                e.preventDefault();
                saveBtn.click();
            }
        }

        // Ctrl/Cmd+Enter: Publish
        if (mod && e.key === 'Enter' && !isInput) {
            const publishBtn = document.querySelector('button[name="action"][value="publish"]');
            if (publishBtn) {
                e.preventDefault();
                publishBtn.click();
            }
        }

        // Escape: Close modals
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal-overlay:not(.hidden)');
            if (modal) {
                modal.classList.add('hidden');
            }
        }

        // Ctrl/Cmd+Shift+P: Toggle preview pane
        if (mod && e.shiftKey && e.key === 'P' && !isInput) {
            const split = document.querySelector('.editor-split');
            if (split) {
                e.preventDefault();
                split.classList.toggle('preview-hidden');
            }
        }

        // ?: Show help
        if (e.key === '?' && !isInput) {
            e.preventDefault();
            const helpModal = document.getElementById('keyboard-help');
            if (helpModal) {
                helpModal.classList.remove('hidden');
            }
        }
    });

    // Modal close button handler
    document.querySelectorAll('.modal-overlay .close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal-overlay').classList.add('hidden');
        });
    });

    // Click outside modal content to close
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.add('hidden');
            }
        });
    });
    } // end admin-body guard

    // --- 4B.1: Table of Contents with IntersectionObserver ---
    const tocContainer = document.querySelector('.post-toc-container');
    if (tocContainer) {
        const headings = document.querySelectorAll('.prose h2, .prose h3');
        if (headings.length >= 3) {
            const toc = document.createElement('nav');
            toc.className = 'post-toc';
            toc.setAttribute('aria-label', 'Table of contents');

            const title = document.createElement('div');
            title.className = 'post-toc-title';
            title.textContent = 'On This Page';
            toc.appendChild(title);

            const ul = document.createElement('ul');
            headings.forEach((heading, index) => {
                if (!heading.id) {
                    heading.id = `heading-${index}`;
                }
                const li = document.createElement('li');
                li.className = heading.tagName === 'H3' ? 'toc-h3' : '';
                const a = document.createElement('a');
                a.href = `#${heading.id}`;
                a.textContent = heading.textContent;
                a.dataset.section = heading.id;
                li.appendChild(a);
                ul.appendChild(li);
            });
            toc.appendChild(ul);
            tocContainer.appendChild(toc);
            tocContainer.style.display = 'block';

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    const id = entry.target.id;
                    const link = toc.querySelector(`a[data-section="${id}"]`);
                    if (link) {
                        link.classList.toggle('active', entry.isIntersecting);
                    }
                });
            }, {
                rootMargin: '-80px 0px -70% 0px',
                threshold: 0
            });

            headings.forEach(h => observer.observe(h));
        }
    }

    // --- 4B.3: Image Lightbox ---
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = lightbox?.querySelector('.lightbox-img');
    const lightboxClose = lightbox?.querySelector('.lightbox-close');

    if (lightbox && lightboxImg) {
        document.querySelectorAll('.prose img').forEach(img => {
            img.style.cursor = 'zoom-in';
            img.addEventListener('click', () => {
                lightboxImg.src = img.src;
                lightboxImg.alt = img.alt;
                lightbox.classList.add('open');
                lightbox.setAttribute('aria-hidden', 'false');
                document.body.style.overflow = 'hidden';
            });
        });

        const closeLightbox = () => {
            lightbox.classList.remove('open');
            lightbox.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
        };

        lightboxClose?.addEventListener('click', closeLightbox);
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) closeLightbox();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && lightbox.classList.contains('open')) {
                closeLightbox();
            }
        });
    }

    // --- 4B.6: Share button color flash ---
    document.querySelectorAll('.share-btn[data-platform]:not([data-platform="copy"])').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const originalBg = this.style.backgroundColor;
            const originalColor = this.style.color;
            const originalBorder = this.style.borderColor;

            this.style.transition = 'background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease';

            const platform = this.dataset.platform;
            const colors = {
                twitter: { bg: '#1da1f2', color: 'white', border: '#1da1f2' },
                facebook: { bg: '#1877f2', color: 'white', border: '#1877f2' },
                linkedin: { bg: '#0a66c2', color: 'white', border: '#0a66c2' },
                hn: { bg: '#ff6600', color: 'white', border: '#ff6600' },
                reddit: { bg: '#ff4500', color: 'white', border: '#ff4500' },
                email: { bg: 'var(--green)', color: 'white', border: 'var(--green)' }
            };

            if (colors[platform]) {
                this.style.backgroundColor = colors[platform].bg;
                this.style.color = colors[platform].color;
                this.style.borderColor = colors[platform].border;
            }

            setTimeout(() => {
                this.style.backgroundColor = originalBg;
                this.style.color = originalColor;
                this.style.borderColor = originalBorder;
            }, 150);
        });
    });

    // --- 5C.2: Prefetch likely next pages ---
    const prefetchedUrls = new Set();
    let prefetchTimer = null;

    document.querySelectorAll('a[href]').forEach(link => {
        const url = link.href;
        if (!url || prefetchedUrls.has(url) || url.startsWith('mailto:') || url.startsWith('tel:')) return;

        link.addEventListener('mouseenter', () => {
            clearTimeout(prefetchTimer);
            prefetchTimer = setTimeout(() => {
                if (prefetchedUrls.has(url)) return;
                prefetchedUrls.add(url);
                const prefetch = document.createElement('link');
                prefetch.rel = 'prefetch';
                prefetch.href = url;
                document.head.appendChild(prefetch);
            }, 100);
        }, { passive: true });
    });

    // --- Nav dropdown toggle ---
    document.querySelectorAll('.nav-dropdown-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const dropdown = btn.closest('.nav-dropdown');
            const isOpen = dropdown.classList.contains('open');
            document.querySelectorAll('.nav-dropdown.open').forEach(d => d.classList.remove('open'));
            if (!isOpen) {
                dropdown.classList.add('open');
                btn.setAttribute('aria-expanded', 'true');
            } else {
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.nav-dropdown.open').forEach(d => {
            d.classList.remove('open');
            d.querySelector('.nav-dropdown-toggle').setAttribute('aria-expanded', 'false');
        });
    });

    // --- Keyboard shortcuts trigger button ---
    document.getElementById('shortcut-trigger')?.addEventListener('click', () => {
        const helpModal = document.getElementById('keyboard-help');
        if (helpModal) {
            helpModal.classList.remove('hidden');
        }
    });

    // --- Upload zone drag-and-drop ---
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const fileInputHidden = document.getElementById('file-input-hidden');
    const uploadForm = document.getElementById('upload-form');

    if (uploadZone && fileInput && uploadForm) {
        uploadZone.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                const formData = new FormData(uploadForm);
                formData.append('file', fileInput.files[0]);
                fetch(uploadForm.action, {
                    method: 'POST',
                    body: formData
                }).then(() => window.location.reload());
            }
        });

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                const formData = new FormData(uploadForm);
                formData.append('file', e.dataTransfer.files[0]);
                fetch(uploadForm.action, {
                    method: 'POST',
                    body: formData
                }).then(() => window.location.reload());
            }
        });
    }
});
