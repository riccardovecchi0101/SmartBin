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
                    const percentLabel = card.querySelector(".percent-label");

                    const fullValue = bin.fulness;

                    if (progress) {
                        animateProgress(progress, fullValue);
                        progress.max = 100;

                        // Aggiorna colore barra
                        progress.classList.remove("is-success", "is-warning", "is-danger");
                        if (fullValue < 40) {
                            progress.classList.add("is-success");
                        } else if (fullValue < 70) {
                            progress.classList.add("is-warning");
                        } else {
                            progress.classList.add("is-danger");
                        }
                    }

                    if (percentLabel) {
                        percentLabel.textContent = `${fullValue}%`;
                    }

                    const infoBtn = card.querySelector(".show-modal");
                    if (infoBtn) {
                        infoBtn.dataset.weight = bin.weight;
                        infoBtn.dataset.distance = bin.distance;
                        infoBtn.dataset.isFull = bin.isFull;
                        infoBtn.dataset.edificio = bin.edificio;
                        infoBtn.dataset.tipo = bin.tipo;
                    }
                }
            });

            console.log("Dati aggiornati via AJAX:", data);
        }
    });
}



function animateProgress(progressEl, targetValue) {
    const current = parseFloat(progressEl.value) || 0;
    const step = (targetValue - current) / 20;
    let progress = current;
    let frame = 0;

    const interval = setInterval(() => {
        progress += step;
        frame++;

        progressEl.value = Math.min(Math.max(progress, 0), 100);

        if (frame >= 20) {
            progressEl.value = targetValue; 
            clearInterval(interval);
        }
    }, 20); 
}