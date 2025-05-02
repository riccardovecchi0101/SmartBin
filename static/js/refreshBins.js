function refreshBins() {
    console.log("Chiamata AJAX inviata");
    $.ajax({
        url: "/refresh_bins",
        method: "GET",
        success: function (data) {
            data.forEach(bin => {
                const card = document.querySelector(`.card[data-id='${bin.id}']`);

                if (card) {
                    const progress = card.querySelector("progress");
                    const fullValue = parseInt(bin.weight) || 0;
                    progress.value = fullValue;
                    progress.textContent = `${fullValue}%`;

                    const percentLabel = card.querySelector("strong");
                    if (percentLabel) {
                        percentLabel.textContent = `${fullValue}%`;
                    }

                    progress.classList.remove("is-success", "is-warning", "is-danger");
                    if (fullValue < 40) {
                        progress.classList.add("is-success");
                    } else if (fullValue < 70) {
                        progress.classList.add("is-warning");
                    } else {
                        progress.classList.add("is-danger");
                    }

                    const infoBtn = card.querySelector(".show-modal");
                    infoBtn.dataset.weight = bin.weight;
                    infoBtn.dataset.floor = bin.floor;
                    infoBtn.dataset.distance = bin.distance;
                    infoBtn.dataset.isFull = bin.isFull;
                }

                console.log("Dati aggiornati via AJAX:", data);
            });
        }
    });
}

setInterval(refreshBins, 5000);