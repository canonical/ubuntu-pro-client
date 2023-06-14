// Override the onLabelClick provided by sphinx_design
window.sdOnLabelClick = window.onLabelClick;
window.onLabelClick = function() {
    sdOnLabelClick.bind(this)();
    // turn off smooth scrolling to avoid jank during this transition
    const html = document.getElementsByTagName("html")[0];
    html.style["scroll-behavior"] = "auto";
    location.hash = "#" + this.getAttribute("for");
    html.style["scroll-behavior"] = "smooth";
}
