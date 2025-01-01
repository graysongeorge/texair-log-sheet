document.querySelector("form").addEventListener("submit", function (event) {
    const firstName = document.getElementById("first_name").value;
    const lastName = document.getElementById("last_name").value;
    const fileInput = document.getElementById("file");

    if (!firstName || !lastName || fileInput.files.length === 0) {
        alert("Please fill out all fields and select a file before submitting.");
        event.preventDefault();
    }
});
