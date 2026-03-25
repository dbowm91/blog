document.addEventListener("DOMContentLoaded", () => {
    // --- Form delete confirmation via data-confirm attribute ---
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', e => {
            if (!confirm(form.dataset.confirm)) e.preventDefault();
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
        if (scrollTimeout) return; // Throttle
        
        scrollTimeout = setTimeout(() => {
            scrollTimeout = null;
            
            // 1. Navbar shrink
            if (navbar) {
                navbar.style.padding = window.scrollY > 60 ? "10px 0" : "16px 0";
            }
            
            // 2. Progress bar
            if (progressBar) {
                const scrollTop = window.scrollY;
                const docHeight = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
                const scrollPercent = (scrollTop / docHeight) * 100;
                progressBar.style.width = `${Math.min(100, scrollPercent)}%`;
            }
            
            // 3. Back to top visibility
            if (window.scrollY > 300) {
                backToTop.classList.add("visible");
            } else {
                backToTop.classList.remove("visible");
            }
        }, 10); // 10ms throttle
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
                            // Fallback for older browsers
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
                        // Even if clipboard fails, we don't want to break the UX
                        console.warn('Failed to copy to clipboard');
                    });
                    return;
                }

                // Fire and forget tracking
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
                        setTimeout(() => {
                            button.textContent = 'Copy';
                        }, 2000);
                    }).catch(() => {
                        // Fallback for older browsers
                        const textarea = document.createElement('textarea');
                        textarea.value = code.textContent;
                        document.body.appendChild(textarea);
                        textarea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textarea);
                        button.textContent = 'Copied!';
                        setTimeout(() => {
                            button.textContent = 'Copy';
                        }, 2000);
                    });
                } else {
                    // Fallback for older browsers
                    const textarea = document.createElement('textarea');
                    textarea.value = code.textContent;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    button.textContent = 'Copied!';
                    setTimeout(() => {
                        button.textContent = 'Copy';
                    }, 2000);
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
            // Generate base ID
            let id = text.toLowerCase()
                .replace(/[^\w\s-]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-')
                .trim();
            
            // Fallback if empty
            if (!id) {
                const headingType = heading.tagName.toLowerCase();
                let counter = 1;
                id = `${headingType}-${counter}`;
                while (usedIds.has(id)) {
                    counter++;
                    id = `${headingType}-${counter}`;
                }
            } else {
                // Ensure uniqueness
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
        
        // Move heading's content into wrapper
        while (heading.firstChild) {
            wrapper.appendChild(heading.firstChild);
        }
        
        heading.appendChild(wrapper);
        heading.appendChild(anchor);
    });

    // --- Lazy loading for images ---
    // Native loading="lazy" is already added in templates
    // This is a fallback for older browsers
    if (!('loading' in HTMLImageElement.prototype)) {
        document.querySelectorAll('img:not([loading])').forEach((img) => {
            const rect = img.getBoundingClientRect();
            if (rect.top > window.innerHeight * 1.5) {
                img.setAttribute('loading', 'lazy');
            }
        });
    }
});
