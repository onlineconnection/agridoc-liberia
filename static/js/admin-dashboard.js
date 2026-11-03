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



// AGRIDOC LIBERIA COUNTY MAP
(() => {
    const mapElement = document.getElementById("liberia-farmer-map");
    const statsElement = document.getElementById("county-stats-data");
    const detailsElement = document.getElementById("county-details");

    if (!mapElement || !statsElement || !detailsElement || !window.L) {
        console.error("Liberia map could not initialize: required elements or Leaflet are missing.");
        return;
    }

    let countyStats;

    try {
        countyStats = JSON.parse(statsElement.textContent || "[]");
    } catch (error) {
        console.error("Could not read county statistics:", error);
        return;
    }

    function normalizeCountyName(name) {
        const normalized = String(name || "").trim().toLowerCase();

        if (normalized === "rivercess" || normalized === "river cess") {
            return "river cess";
        }

        return normalized;
    }

    const statsByCounty = new Map(
        countyStats.map(item => [
            normalizeCountyName(item.county),
            item
        ])
    );

    const maxFarmers = Math.max(
        1,
        ...countyStats.map(item => Number(item.farmer_count) || 0)
    );

    function getCountyStats(name) {
        return statsByCounty.get(normalizeCountyName(name)) || {
            county: name,
            farmer_count: 0,
            percentage: 0
        };
    }

    function getCountyColor(count) {
        const ratio = count / maxFarmers;

        if (count === 0) return "#e5eee8";
        if (ratio <= 0.25) return "#c5ddc9";
        if (ratio <= 0.50) return "#91bd9b";
        if (ratio <= 0.75) return "#4f9366";
        return "#194b35";
    }

    mapElement.style.height = "460px";

    const map = L.map(mapElement, {
        scrollWheelZoom: false
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    let selectedLayer = null;
    let countyLayer = null;

    function showCountyDetails(name) {
        const stats = getCountyStats(name);

        const heading = document.createElement("h3");
        heading.textContent = stats.county;

        const count = document.createElement("p");
        count.textContent = `Registered farmers: ${Number(stats.farmer_count).toLocaleString()}`;

        const percentage = document.createElement("p");
        percentage.textContent = `Share of recorded county registrations: ${Number(stats.percentage).toFixed(1)}%`;

        detailsElement.replaceChildren(heading, count, percentage);
    }

    fetch("/static/data/liberia-counties.geojson")
        .then(response => {
            if (!response.ok) {
                throw new Error(`GeoJSON request failed: HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(geojson => {
            countyLayer = L.geoJSON(geojson, {
                style: feature => {
                    const name = feature.properties.name;
                    const stats = getCountyStats(name);

                    return {
                        color: "#ffffff",
                        weight: 1.5,
                        fillColor: getCountyColor(Number(stats.farmer_count) || 0),
                        fillOpacity: 0.85
                    };
                },

                onEachFeature: (feature, layer) => {
                    const countyName = feature.properties.name;
                    const stats = getCountyStats(countyName);

                    layer.bindTooltip(
                        `${countyName}: ${Number(stats.farmer_count).toLocaleString()} farmers`
                    );

                    layer.on({
                        mouseover: event => {
                            event.target.setStyle({
                                weight: 3,
                                color: "#d6b343",
                                fillOpacity: 1
                            });
                        },

                        mouseout: event => {
                            countyLayer.resetStyle(event.target);

                            if (selectedLayer === event.target) {
                                event.target.setStyle({
                                    weight: 3,
                                    color: "#d6b343",
                                    fillOpacity: 1
                                });
                            }
                        },

                        click: event => {
                            if (selectedLayer) {
                                countyLayer.resetStyle(selectedLayer);
                            }

                            selectedLayer = event.target;

                            selectedLayer.setStyle({
                                weight: 3,
                                color: "#d6b343",
                                fillOpacity: 1
                            });

                            showCountyDetails(countyName);
                        }
                    });
                }
            }).addTo(map);

            map.fitBounds(countyLayer.getBounds(), {
                padding: [20, 20]
            });
        })
        .catch(error => {
            console.error("Could not load Liberia county map:", error);
            detailsElement.textContent =
                "The county map could not be loaded. Please check your connection and try again.";
        });
})();
