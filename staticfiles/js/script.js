// ---- POPUP ----

// Function to close the popup by gradually reducing opacity and then removing it from the DOM
function closePopup(element) {
    element.parentElement.style.opacity = "0"; // set the opacity of parent element (popup card) to 0
    setTimeout(function () {
        element.parentElement.remove();
    }, 500); // remove the opop-up card after a delay of 5 ms
}

function showPopupSlowly(popup) {
    popup.style.opacity = "1"; // set the opacity to be 1
}

function hidePopupSlowly(popup) {
    popup.style.opacity = "0";
    setTimeout(function () {
        popup.remove();
    }, 500);
}

document.addEventListener("DOMContentLoaded", function () {
    var popup = document.querySelector(".popup-card");
    if (popup) {
        showPopupSlowly(popup);
        setTimeout(function () {
            hidePopupSlowly(popup);
        }, 5000); // 5 seconds
    }
});
