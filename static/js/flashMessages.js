document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
        let messages = document.querySelectorAll(".notification");
        messages.forEach(function (message) {
            message.style.display = "none";
        });
    }, 3000);
});