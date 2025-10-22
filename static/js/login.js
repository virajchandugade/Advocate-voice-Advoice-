
$("#name-key").submit(function (event) {
    event.preventDefault();

    const username = $("#username").val().trim();
    const licenseKey = $("#userkey").val().trim();

    $.ajax({
        url: "/login",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ username, licenseKey }),
        success: function (response) {
            if (response.success) {
                localStorage.setItem("username", username);
                localStorage.setItem("licenseKey", licenseKey);
                window.location.href = response.redirect;
            } else {
                $("#message").text(response.message).css("color", "red");
            }
        },
        error: function (xhr) {
            const errorMsg = xhr.responseJSON?.message || "An error occurred. Please try again.";
            $("#message").text(errorMsg).css("color", "red");
        }
    });
});

