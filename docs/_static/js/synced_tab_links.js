// Override the onLabelClick provided by sphinx_design
window.sdOnLabelClick = window.onLabelClick;
window.onLabelClick = function() {
    // Get the position of the clicked element within the viewport before the document height changes
    const elementTopBefore = this.getBoundingClientRect().top;

    // Call the original, this changes all of the synced tabs and changes the height of the document
    sdOnLabelClick.bind(this)();

    // Get the new position of the clicked element
    const elementTopAfter = this.getBoundingClientRect().top;

    // Scroll the difference so that it is back in the same place where it was before the change
    window.scroll({
        top: document.documentElement.scrollTop + (elementTopAfter - elementTopBefore),
        left: document.documentElement.scrollLeft,
        behavior: "instant",
    });
