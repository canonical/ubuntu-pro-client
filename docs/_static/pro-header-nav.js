// Ubuntu Pro-specific header navigation behaviour.
// Toggles the "Pro services" dropdown in the documentation header
// (docs/_templates/header.html). The canonical-sphinx theme only handles the
// default ".more-links-dropdown", so this handler is required for the
// Pro-specific ".pro-services-dropdown".
$(document).ready(function() {
    $(document).on("click", function () {
        $(".pro-services-dropdown").hide();
    });

    $('.nav-pro-services').click(function(event) {
        $('.pro-services-dropdown').toggle();
        event.stopPropagation();
    });
})
