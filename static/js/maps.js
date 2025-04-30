document.addEventListener("DOMContentLoaded", () => {
    const bins = window.binsFromServer;

    const map = L.map('map').setView([44.65, 10.92], 16);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
    }).addTo(map);

    bins.forEach(bin => {
        const lat = bin.latitude;
        const lon = bin.longitude;
        const status = bin.is_full ? "Pieno" : "Vuoto";

        L.marker([lat, lon]).addTo(map)
            .bindPopup(`
                <strong>Bin ID:</strong> ${bin.id}<br>
                <strong>Stato:</strong> ${status}<br>
                <strong>Peso:</strong> ${bin.weight}g<br>
                <strong>Distanza:</strong> ${bin.distance}cm<br>
                <strong>Piano:</strong> ${bin.floor}
            `);
    });
});
