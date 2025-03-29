document.addEventListener("DOMContentLoaded", function () {
    let closeButtons = document.querySelectorAll(".notification .delete");

    closeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            this.parentElement.style.display = "none";
        });
    });
});