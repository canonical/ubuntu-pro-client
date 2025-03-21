$(document).ready(function() {
    $(document).on("click", function () {
        $(".pro-services-dropdown").hide();
    });

    $('.nav-pro-services').click(function(event) {
        $('.pro-services-dropdown').toggle();
        event.stopPropagation();
    });
})
