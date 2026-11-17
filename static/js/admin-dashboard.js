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
    const detailsToggleButton = document.getElementById("toggle-county-details");

    if (detailsToggleButton) {
        detailsToggleButton.addEventListener("click", () => {
            detailsElement.hidden = !detailsElement.hidden;

            const detailsVisible = !detailsElement.hidden;

            detailsToggleButton.textContent = detailsVisible
                ? "Hide County Details"
                : "Show County Details";

            detailsToggleButton.setAttribute(
                "aria-expanded",
                String(detailsVisible)
            );
        });
    }


    // Skip map initialization on pages that do not contain the map.
    if (!mapElement) return;

    if (!statsElement || !detailsElement || !window.L) {
        console.error("Liberia map could not initialize: required elements or Leaflet are missing.");
        return;
    }

    let countyStats;

    try {
        countyStats = JSON.parse(statsElement.textContent || "[]") || [];
    } catch (error) {
        console.error("Could not read map statistics:", error);
        return;
    }

    function normalizeName(name) {
        const normalized = String(name || "").trim().toLowerCase();

        if (normalized === "rivercess" || normalized === "river cess") {
            return "river cess";
        }

        return normalized.replace(/\s+/g, " ");
    }

    const statsByCounty = new Map(
        countyStats.map(item => [normalizeName(item.county), item])
    );

    let currentMapMode = "standard";

    const maxFarmers = Math.max(
        1,
        ...countyStats.map(item => Number(item.farmer_count) || 0)
    );

    function getCountyStats(name) {
        return statsByCounty.get(normalizeName(name)) || {
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

    const baseLayers = {
        street: L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }),
        satellite: L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            {
                attribution: 'Sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
                maxZoom: 19
            }
        )
    };

    const transportationOverlay = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
        {
            attribution: 'Transportation data: Esri, HERE, Garmin, OpenStreetMap contributors, and the GIS User Community',
            maxZoom: 19,
            opacity: 0.95
        }
    );

    let activeBaseLayer = baseLayers.street;
    activeBaseLayer.addTo(map);

    const basemapSelect = document.getElementById("map-basemap");

    basemapSelect.addEventListener("change", () => {
        const selectedBasemap = basemapSelect.value;

        map.removeLayer(activeBaseLayer);
        if (map.hasLayer(transportationOverlay)) {
            map.removeLayer(transportationOverlay);
        }

        activeBaseLayer = selectedBasemap === "street"
            ? baseLayers.street
            : baseLayers.satellite;

        activeBaseLayer.addTo(map);

        if (selectedBasemap === "hybrid") {
            transportationOverlay.addTo(map);
        }

        map.invalidateSize();
    });

    const mapViewport = document.getElementById("map-viewport");
    const fullscreenButton = document.getElementById("map-fullscreen");
    const modeButtons = document.querySelectorAll("[data-map-mode]");
    const countyOverlayButton = document.getElementById("toggle-county-overlay");

    let selectedLayer = null;
    let countyLayer = null;
    let countyOverlayVisible = true;

    if (countyOverlayButton) {
        countyOverlayButton.addEventListener("click", () => {
            countyOverlayVisible = !countyOverlayVisible;

            if (countyLayer) {
                if (countyOverlayVisible) {
                    countyLayer.addTo(map);
                } else {
                    map.removeLayer(countyLayer);
                }
            }

            countyOverlayButton.textContent = countyOverlayVisible
                ? "County Overlay: ON"
                : "County Overlay: OFF";

            countyOverlayButton.classList.toggle("active", countyOverlayVisible);
            countyOverlayButton.setAttribute(
                "aria-pressed",
                String(countyOverlayVisible)
            );
        });
    }

    document.getElementById("map-zoom-in").addEventListener("click", () => {
        map.zoomIn();
    });

    document.getElementById("map-zoom-out").addEventListener("click", () => {
        map.zoomOut();
    });

    fullscreenButton.addEventListener("click", () => {
        if (!document.fullscreenElement) {
            mapViewport.requestFullscreen().catch(error => {
                console.error("Could not enter map fullscreen:", error);
            });
        } else {
            document.exitFullscreen();
        }
    });

    document.addEventListener("fullscreenchange", () => {
        const isFullscreen = Boolean(document.fullscreenElement);
        fullscreenButton.textContent = isFullscreen ? "Exit Fullscreen" : "Fullscreen";
        map.invalidateSize();
    });

    function updateMapMode(mode) {
        currentMapMode = mode;

        modeButtons.forEach(button => {
            const active = button.dataset.mapMode === mode;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });

        if (countyLayer) {
            countyLayer.setStyle(feature => {
                const stats = getCountyStats(feature.properties.name);
                return {
                    fillColor: mode === "density"
                        ? getCountyColor(Number(stats.farmer_count) || 0)
                        : "#c5d8ca"
                };
            });
        }
    }

    modeButtons.forEach(button => {
        button.addEventListener("click", () => {
            updateMapMode(button.dataset.mapMode);
        });
    });

    function showCountyDetails(name) {
        const stats = getCountyStats(name);

        const heading = document.createElement("h3");
        heading.textContent = stats.county;

        const count = document.createElement("p");
        count.textContent =
            `Registered farmers: ${Number(stats.farmer_count).toLocaleString()}`;

        const percentage = document.createElement("p");
        percentage.textContent =
            `Share of recorded county registrations: ${Number(stats.percentage).toFixed(1)}%`;

        const instruction = document.createElement("p");
        instruction.textContent =
            "Select a county in the directory or on the map to view its registration summary.";

        detailsElement.replaceChildren(heading, count, percentage, instruction);
    }

    function selectCounty(countyName, targetLayer = null) {
        if (!targetLayer && countyLayer) {
            countyLayer.eachLayer(layer => {
                if (normalizeName(layer.feature.properties.name) ===
                    normalizeName(countyName)) {
                    targetLayer = layer;
                }
            });
        }

        if (!targetLayer) return;

        if (selectedLayer) {
            countyLayer.resetStyle(selectedLayer);
        }

        selectedLayer = targetLayer;
        selectedLayer.setStyle({
            weight: 3,
            color: "#d6b343",
            fillOpacity: 1
        });

        document.querySelectorAll("#county-list button").forEach(button => {
            const active = normalizeName(button.dataset.county) ===
                normalizeName(countyName);
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });

        map.fitBounds(targetLayer.getBounds(), {
            padding: [35, 35],
            maxZoom: 8
        });

    }

    function renderCountyDirectory(features) {
        const list = document.getElementById("county-list");
        const search = document.getElementById("county-search");

        if (!list || !search) return;

        list.replaceChildren();

        features
            .slice()
            .sort((a, b) =>
                a.properties.name.localeCompare(b.properties.name)
            )
            .forEach(feature => {
                const countyName = feature.properties.name;
                const stats = getCountyStats(countyName);

                const button = document.createElement("button");
                button.type = "button";
                button.dataset.county = countyName;
                button.setAttribute("aria-pressed", "false");

                const name = document.createElement("span");
                name.textContent = countyName;

                const count = document.createElement("span");
                count.className = "county-count";
                count.textContent =
                    Number(stats.farmer_count).toLocaleString();

                button.append(name, count);
                button.addEventListener("click", () => {
                    selectCounty(countyName);
                });

                list.appendChild(button);
            });

        search.addEventListener("input", () => {
            const query = normalizeName(search.value);

            list.querySelectorAll("button").forEach(button => {
                button.hidden = !normalizeName(button.dataset.county)
                    .includes(query);
            });
        });
    }

    Promise.all([
        fetch("/static/data/liberia-counties.geojson").then(response => {
            if (!response.ok) {
                throw new Error(`County GeoJSON request failed: HTTP ${response.status}`);
            }
            return response.json();
        }),
        fetch("/static/data/liberia-neighbor-mask.geojson").then(response => {
            if (!response.ok) {
                throw new Error(`Neighbor mask request failed: HTTP ${response.status}`);
            }
            return response.json();
        })
    ])
        .then(([geojson, neighborMaskGeojson]) => {
            // Cover neighboring land while keeping the ocean basemap visible.
            L.geoJSON(neighborMaskGeojson, {
                interactive: false,
                style: {
                    stroke: false,
                    fillColor: "#edf5ef",
                    fillOpacity: 1
                }
            }).addTo(map);

            // Liberia's counties are drawn above the neighboring-land mask.
            countyLayer = L.geoJSON(geojson, {
                style: feature => {
                    const name = feature.properties.name;
                    const stats = getCountyStats(name);

                    return {
                        color: "#ffffff",
                        weight: 1.5,
                        fillColor: currentMapMode === "density"
                            ? getCountyColor(Number(stats.farmer_count) || 0)
                            : "#c5d8ca",
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
                            selectCounty(countyName, event.target);
                        }
                    });
                }
            });

            if (countyOverlayVisible) {
                countyLayer.addTo(map);
            }

            renderCountyDirectory(geojson.features || []);

            const liberiaBounds = countyLayer.getBounds();

            document.getElementById("map-fit-liberia").addEventListener("click", () => {
                map.fitBounds(liberiaBounds, { padding: [20, 20] });
            });

            map.fitBounds(liberiaBounds, {
                padding: [20, 20]
            });

            map.setMaxBounds(liberiaBounds.pad(0.005));
            map.setMinZoom(map.getBoundsZoom(liberiaBounds));
        })
        .catch(error => {
            console.error("Could not load Liberia county map:", error);
            detailsElement.textContent =
                "The county map could not be loaded. Please check your connection and try again.";
        });
})();
