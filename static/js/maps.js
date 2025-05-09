document.addEventListener("DOMContentLoaded", () => {
    const bins = window.binsFromServer.filter(b => b.latitude && b.longitude);

    const map = L.map('map').setView([44.6501, 10.9215], 17);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const fullBins = [];
    const binMarkers = {};

    bins.forEach(bin => {
        const latlng = [bin.latitude, bin.longitude];
        const isFull = bin.weight > 18 && bin.distance < 20;

        const icon = new L.Icon({
            iconUrl: isFull
                ? "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png"
                : "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
            shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        });

        const marker = L.marker(latlng, {icon: icon}).addTo(map);
        marker.bindPopup(`
            <div>
                <strong>Cestino #${bin.id}</strong><br>
                <b>Peso:</b> ${bin.weight} Kg<br>
                <b>Distanza:</b> ${bin.distance} cm<br>
                <b>Stato:</b> ${isFull ? "Pieno" : "Vuoto"}
            </div>
        `);
        binMarkers[bin.id] = marker

        if (isFull) {
            fullBins.push({
                id: bin.id,
                coords: [bin.latitude, bin.longitude],
                lonlat: [bin.longitude, bin.latitude],
                data: bin
            });
        }
    });

    const binList = document.getElementById("bin-list");
    fullBins.forEach((bin) => {
        const item = document.createElement("li");
        item.innerHTML = `
            <strong>#${bin.id}</strong> | Piano: ${bin.data.floor} | Peso: ${bin.data.weight} Kg | Distanza: ${bin.data.distance} cm
        `;
        item.addEventListener("click", () => {
            map.setView(bin.coords, 18);
            binMarkers[bin.id].openPopup();
        });
        binList.appendChild(item);
    });

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async (position) => {
            const userPos = [position.coords.longitude, position.coords.latitude];

            const userMarker = L.marker([userPos[1], userPos[0]], {title: "Tu sei qui"}).addTo(map);
            userMarker.bindPopup("Posizione attuale").openPopup();

            const coordinates = [userPos, ...fullBins.map(b => b.lonlat)];
            if (coordinates.length < 2) return;

            const response = await fetch("https://api.openrouteservice.org/v2/directions/foot-walking/geojson", {
                method: "POST",
                headers: {
                    "Authorization": "5b3ce3597851110001cf62481e143dcd0a5a47df84a55dc91a39c19b",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({coordinates}),
            });

            const data = await response.json();

            const summary = data.features[0].properties.summary;
            document.getElementById("route-distance").textContent = `Distanza: ${summary.distance.toFixed(1)} m`;
            document.getElementById("route-duration").textContent = `Durata: ${Math.round(summary.duration / 60)} min`;

            const route = L.geoJSON(data, {
                style: {color: "blue", weight: 4}
            }).addTo(map);
            map.fitBounds(route.getBounds());
        });
    } else {
        console.log("Geolocalizzazione non disponibile.");
    }
});
