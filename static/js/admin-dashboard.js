(() => {
            const toggle = document.getElementById("menu-toggle");
            const overlay = document.getElementById("mobile-overlay");
            const sidebar = document.getElementById("sidebar");

            function closeMenu() {
                document.body.classList.remove("menu-open");
                toggle.setAttribute("aria-expanded", "false");
                toggle.setAttribute("aria-label", "Open navigation");
            }

            toggle.addEventListener("click", () => {
                const isOpen = document.body.classList.toggle("menu-open");
                toggle.setAttribute("aria-expanded", String(isOpen));
                toggle.setAttribute(
                    "aria-label",
                    isOpen ? "Close navigation" : "Open navigation"
                );
            });

            overlay.addEventListener("click", closeMenu);

            sidebar.querySelectorAll("a").forEach(link => {
                link.addEventListener("click", closeMenu);
            });

            document.addEventListener("keydown", event => {
                if (event.key === "Escape") closeMenu();
            });

            window.addEventListener("resize", () => {
                if (window.innerWidth > 760) closeMenu();
            });
        })();
