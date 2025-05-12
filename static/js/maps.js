document.addEventListener("DOMContentLoaded", () => {
    let map = L.map('map').setView([44.6501, 10.9215], 17);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const binsFromServer = window.binsFromServer || [];
    const markerById = {};
    let userMarker = null;
    let userCoords = null;
    let routeLayerFoot = null;
    let routeLayerCar = null;
    let lastFullBinsSignature = "";
    let bins = [];

    const userIcon = L.icon({
        iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    const redIcon = L.icon({
        iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    const greenIcon = L.icon({
        iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    function buildPopup(bin) {
        return `<b>Cestino #${bin.id}</b><br>
        <b>Edificio:</b> ${bin.edificio}<br>
        <b>Peso:</b> ${bin.weight} Kg<br>
        <b>Distanza Riempimento:</b> ${bin.distance} cm<br>
        <b>Stato:</b> ${bin.is_full ? "Pieno" : "Vuoto"}`;
    }

    function addMarkers(bins) {
        bins.forEach((bin) => {
            if (!bin.latitude || !bin.longitude)
                return;

            const latlng = [bin.latitude, bin.longitude];
            const icon = bin.is_full ? redIcon : greenIcon;
            const marker = L.marker(latlng, {icon}).addTo(map);
            marker.bindPopup(buildPopup(bin));
            markerById[bin.id] = marker;
        });
    }

    function updateBinsLive(newBins) {
        bins = newBins;
        bins.forEach((bin) => {
            if (!bin.latitude || !bin.longitude)
                return;

            const marker = markerById[bin.id];
            const newLatLng = [bin.latitude, bin.longitude];
            const icon = bin.is_full ? redIcon : greenIcon;

            if (marker) {
                const current = marker.getLatLng();

                if (!current.equals(newLatLng)) {
                    const steps = 10;
                    let i = 0;
                    const deltaLat = (newLatLng[0] - current.lat) / steps;
                    const deltaLng = (newLatLng[1] - current.lng) / steps;

                    const animate = () => {
                        if (i < steps) {
                            const lat = current.lat + deltaLat * i;
                            const lng = current.lng + deltaLng * i;
                            marker.setLatLng([lat, lng]);
                            i++;
                            setTimeout(animate, 40);
                        } else {
                            marker.setLatLng(newLatLng);
                        }
                    };

                    animate();
                }

                marker.setIcon(icon);
                marker.setPopupContent(buildPopup(bin));
            } else {
                const newMarker = L.marker(newLatLng, {icon}).addTo(map);
                newMarker.bindPopup(buildPopup(bin));
                markerById[bin.id] = newMarker;
            }
        });

        const fullBinIds = bins
            .filter(bin => bin.is_full)
            .map(bin => `${bin.id}:${bin.latitude},${bin.longitude},${bin.is_full}`)
            .sort()
            .join("|");

        if (fullBinIds !== lastFullBinsSignature) {
            lastFullBinsSignature = fullBinIds;
            calculateRoute("foot");
            calculateRoute("driving-car");
        }

        const list = document.getElementById("next-bin-info");

        if (userCoords && list) {
            const binsOrdered = bins
                .filter(b => b.is_full && b.latitude && b.longitude)
                .map(b => ({
                    id: b.id,
                    distanza: Math.sqrt(
                        Math.pow(b.latitude - userCoords.lat, 2) +
                        Math.pow(b.longitude - userCoords.lng, 2)
                    )
                }))
                .sort((a, b) => a.distanza - b.distanza);

            list.innerHTML = "";
            binsOrdered.forEach((b, i) => {
                let distanzaMetri = b.distanza * 111000;
                const distanzaTesto = distanzaMetri >= 1000
                    ? `${(distanzaMetri / 1000).toFixed(2)} km`
                    : `${distanzaMetri.toFixed(0)} m`;

                const li = document.createElement("li");
                li.textContent = `Cestino #${b.id} - ${distanzaTesto}`;
                list.appendChild(li);
            });
        }

        const binList = document.getElementById("bin-list");
        if (binList) {
            binList.innerHTML = "";
            bins.forEach(bin => {
                if (bin.is_full) {
                    const item = document.createElement("li");
                    item.innerHTML = `
                    <strong>Cestino #${bin.id}</strong> | Edificio: ${bin.edificio ?? '-'} | Peso: ${bin.weight} Kg | Distanza Riempimento: ${bin.distance} cm
                `;
                    item.addEventListener("click", () => {
                        const marker = markerById[bin.id];
                        if (marker) {
                            map.setView(marker.getLatLng(), 18);
                            marker.openPopup();
                        }
                    });
                    binList.appendChild(item);
                }
            });
        }
    }

    function calculateRoute(type = "foot") {
        if (!userCoords)
            return;

        const fullBins = bins
            .filter((bin) => bin.is_full && bin.latitude && bin.longitude)
            .map((bin) => [bin.longitude, bin.latitude]);

        if (fullBins.length === 0) {
            if (routeLayerFoot)
                map.removeLayer(routeLayerFoot);
            if (routeLayerCar)
                map.removeLayer(routeLayerCar);

            return;
        }

        const coordinates = [
            [userCoords.lng, userCoords.lat],
            ...fullBins,
        ];

        const mode = type === "foot" ? "foot-walking" : "driving-car";

        fetch(`https://api.openrouteservice.org/v2/directions/${mode}/geojson`, {
            method: "POST",
            headers: {
                "Authorization": "5b3ce3597851110001cf62481e143dcd0a5a47df84a55dc91a39c19b",
                "Content-Type": "application/json",
            },
            body: JSON.stringify({coordinates}),
        })
            .then((res) => res.json())
            .then((geojson) => {
                const summary = geojson.features[0].properties.summary;
                if (!summary)
                    return;

                const line = L.geoJSON(geojson, {
                    style: {color: type === "foot" ? "blue" : "orange", weight: 4},
                });

                if (type === "foot") {
                    if (routeLayerFoot)
                        map.removeLayer(routeLayerFoot);

                    routeLayerFoot = line.addTo(map);

                    const distFoot = document.getElementById("route-distance-foot");
                    const timeFoot = document.getElementById("route-duration-foot");

                    if (distFoot && timeFoot) {
                        const distanza = summary.distance;
                        const durataSec = summary.duration;

                        const distanzaTesto = distanza >= 1000
                            ? `${(distanza / 1000).toFixed(2)} km`
                            : `${Math.round(distanza)} m`;

                        const durataMin = Math.round(durataSec / 60);
                        const durataTesto = durataMin >= 60
                            ? `${Math.floor(durataMin / 60)}h ${durataMin % 60}m`
                            : `${durataMin} min`;

                        distFoot.textContent = `Distanza: ${distanzaTesto}`;
                        timeFoot.textContent = `Durata: ${durataTesto}`;
                    }
                } else {
                    if (routeLayerCar)
                        map.removeLayer(routeLayerCar);

                    routeLayerCar = line.addTo(map);

                    const distCar = document.getElementById("route-distance-car");
                    const timeCar = document.getElementById("route-duration-car");

                    if (distCar && timeCar) {
                        const distanza = summary.distance;
                        const durataSec = summary.duration;

                        const distanzaTesto = distanza >= 1000
                            ? `${(distanza / 1000).toFixed(2)} km`
                            : `${Math.round(distanza)} m`;

                        const durataMin = Math.round(durataSec / 60);
                        const durataTesto = durataMin >= 60
                            ? `${Math.floor(durataMin / 60)}h ${durataMin % 60}m`
                            : `${durataMin} min`;

                        distCar.textContent = `Distanza: ${distanzaTesto}`;
                        timeCar.textContent = `Durata: ${durataTesto}`;
                    }
                }
            })
            .catch(console.error);
    }

    navigator.geolocation.getCurrentPosition((pos) => {
        const {latitude, longitude} = pos.coords;
        userCoords = {lat: latitude, lng: longitude};
        userMarker = L.marker([latitude, longitude], {icon: userIcon}).addTo(map).bindPopup("Posizione attuale");
        map.setView([latitude, longitude], 13);

        // addMarkers(binsFromServer);
    });

    setInterval(() => {
        fetch('/refresh_bins')
            .then((res) => res.json())
            .then((data) => updateBinsLive(data));
    }, 1000);
});
