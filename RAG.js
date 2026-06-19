let select, link, popover;

// Initialize all popover elements
function initPopovers() {
    // Static popovers
    const staticPopoverTriggers = document.querySelectorAll(".popover-help");

    staticPopoverTriggers.forEach(el => {
        new bootstrap.Popover(el, {
            trigger: "click"
        });

        el.addEventListener('click', e => e.preventDefault());
    });

    // Dynamic popover (doc info)
    link = document.getElementById("doc-info-link");
    if (link) {
        popover = new bootstrap.Popover(link, {
            trigger: "click",
            content: "No document selected",
            html: false
        });

        link.addEventListener('click', e => e.preventDefault());
    }

    // Click outside to close
    document.addEventListener('click', handleClickOutside);
}

// Handle click outside any popover
function handleClickOutside(event) {
    const popoverElList = document.querySelectorAll('[data-bs-toggle="popover"]');
    popoverElList.forEach(el => {
        const popoverInstance = bootstrap.Popover.getInstance(el);
        const isClickInsideTrigger = el.contains(event.target);
        const isClickInsidePopover = document.querySelector('.popover')?.contains(event.target);

        if (popoverInstance && !isClickInsideTrigger && !isClickInsidePopover) {
            popoverInstance.hide();
        }
    });
}

// Handle select change
function handleDocumentChange(event) {
    const selectedValue = event.target.value;

    if (!selectedValue) {
        updatePopoverContent("No document selected");
        return;
    }

    showPopoverSpinner();
    fetchDescription(selectedValue);
}

// Fetch document description from the server
function fetchDescription(docName) {
    showPopoverSpinner();

    fetch("/get_description", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ doc_name: docName })
    })
    .then(response => response.json())
    .then(data => updatePopoverContent(data.description))
    .catch(err => {
        console.error("Error fetching description:", err);
        updatePopoverContent("Error retrieving description.");
    });
}

// Show loading spinner in popover
function showPopoverSpinner() {
    const spinnerHTML = `
        <div class="d-flex justify-content-center align-items-center" style="height: 2rem;">
            <div class="spinner-border text-primary" role="status" style="width: 1.5rem; height: 1.5rem;"></div>
        </div>
    `;
    updatePopoverContent(spinnerHTML, true);
}

// Update the content of the document info popover
function updatePopoverContent(contentHTML, isHTML = false) {
    if (!link) return;

    bootstrap.Popover.getInstance(link)?.dispose();

    popover = new bootstrap.Popover(link, {
        trigger: "click",
        content: contentHTML,
        html: isHTML
    });

    popover.show();
}

// Initialize everything on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    select = document.getElementById("selected_document");
    initPopovers();

    if (select) {
        select.addEventListener("change", handleDocumentChange);
    }
});
