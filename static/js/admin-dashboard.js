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
    const districtStatsElement = document.getElementById("district-stats-data");
    const detailsElement = document.getElementById("county-details");

    if (!mapElement || !statsElement || !districtStatsElement ||
        !detailsElement || !window.L) {
        console.error("Liberia map could not initialize: required elements or Leaflet are missing.");
        return;
    }

    let countyStats;
    let districtStats;

    try {
        countyStats = JSON.parse(statsElement.textContent || "[]") || [];
        districtStats = JSON.parse(districtStatsElement.textContent || "[]") || [];
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

    function districtKey(county, district) {
        return `${normalizeName(county)}|${normalizeName(district)}`;
    }

    const statsByCounty = new Map(
        countyStats.map(item => [normalizeName(item.county), item])
    );

    const statsByDistrict = new Map(
        districtStats.map(item => [
            districtKey(item.county, item.district),
            Number(item.farmer_count) || 0
        ])
    );

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

    let selectedLayer = null;
    let countyLayer = null;
    let districtDataPromise = null;

    const districtLayer = L.layerGroup().addTo(map);

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
            "District markers show farmer registrations by district. Select a marker for details.";

        detailsElement.replaceChildren(heading, count, percentage, instruction);
    }

    function showDistrictDetails(county, district, count) {
        const heading = document.createElement("h3");
        heading.textContent = `${district}, ${county}`;

        const paragraph = document.createElement("p");
        paragraph.textContent =
            `Registered farmers in this district: ${count.toLocaleString()}`;

        detailsElement.replaceChildren(heading, paragraph);
    }

    function loadDistrictsForCounty(countyName) {
        districtLayer.clearLayers();
        showCountyDetails(countyName);

        if (!districtDataPromise) {
            districtDataPromise = fetch("/static/data/liberia-districts.json")
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`District data request failed: HTTP ${response.status}`);
                    }
                    return response.json();
                });
        }

        districtDataPromise
            .then(districts => {
                const matchingDistricts = districts.filter(district =>
                    normalizeName(district.parent?.name?.en) ===
                    normalizeName(countyName)
                );

                const markers = [];

                matchingDistricts.forEach(district => {
                    const districtName =
                        district.name?.en || district.name?.local;

                    const lat = Number(district.geo?.lat);
                    const lon = Number(district.geo?.lon);

                    if (!districtName || !Number.isFinite(lat) ||
                        !Number.isFinite(lon)) {
                        return;
                    }

                    const count = statsByDistrict.get(
                        districtKey(countyName, districtName)
                    ) || 0;

                    const marker = L.circleMarker([lat, lon], {
                        radius: 7,
                        color: "#ffffff",
                        weight: 2,
                        fillColor: "#194b35",
                        fillOpacity: 0.95
                    });

                    marker.bindPopup(
                        `<strong>${districtName}</strong><br>` +
                        `Registered farmers: ${count.toLocaleString()}`
                    );

                    marker.on("click", () => {
                        showDistrictDetails(countyName, districtName, count);
                    });

                    marker.addTo(districtLayer);
                    markers.push(marker);
                });

                if (markers.length === 0) {
                    const message = document.createElement("p");
                    message.textContent =
                        "No district coordinates were found for this county.";
                    detailsElement.appendChild(message);
                }
            })
            .catch(error => {
                console.error("Could not load district markers:", error);

                const message = document.createElement("p");
                message.textContent =
                    "District information could not be loaded. Please try again.";
                detailsElement.appendChild(message);
            });
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
                        fillColor: getCountyColor(
                            Number(stats.farmer_count) || 0
                        ),
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

                            loadDistrictsForCounty(countyName);
                        }
                    });
                }
            }).addTo(map);

            const liberiaBounds = countyLayer.getBounds();

            map.fitBounds(liberiaBounds, {
                padding: [20, 20]
            });

            map.setMaxBounds(liberiaBounds.pad(0.03));
            map.setMinZoom(map.getBoundsZoom(liberiaBounds));
        })
        .catch(error => {
            console.error("Could not load Liberia county map:", error);
            detailsElement.textContent =
                "The county map could not be loaded. Please check your connection and try again.";
        });
})();
