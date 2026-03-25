document.addEventListener("DOMContentLoaded", () => {
    // --- Navbar shrink on scroll ---
    const navbar = document.querySelector(".navbar");
    if (navbar) {
        window.addEventListener(
            "scroll",
            () => {
                if (window.scrollY > 60) {
                    navbar.style.padding = "10px 0";
                } else {
                    navbar.style.padding = "16px 0";
                }
            },
            { passive: true }
        );
    }

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
                    navigator.clipboard.writeText(shareUrl).then(() => {
                        const original = btn.innerHTML;
                        btn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
                        setTimeout(() => { btn.innerHTML = original; }, 1500);
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
});
