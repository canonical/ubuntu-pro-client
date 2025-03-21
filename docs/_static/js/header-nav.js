$(document).ready(function() {
    $(document).on("click", function () {
        $(".more-links-dropdown").hide();
        $(".pro-services-dropdown").hide();
    });

    $('.nav-more-links').click(function(event) {
        $('.more-links-dropdown').toggle();
        $(".pro-services-dropdown").hide();
        event.stopPropagation();
    });

    $('.nav-pro-services').click(function(event) {
        $('.pro-services-dropdown').toggle();
        $(".more-links-dropdown").hide();
        event.stopPropagation();
    });
})
