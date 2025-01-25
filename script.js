function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
}

function searchAndHighlight() {
    const query = document.getElementById('search').value.toLowerCase();
    const items = document.querySelectorAll('#tree span');

    // If the search query is empty, reset the tree
    if (!query) {
        resetTree();
        return;
    }

    items.forEach(item => {
        const listItem = item.closest('li');
        const parentUl = listItem.closest('ul');
        const parentSpan = parentUl?.previousElementSibling;

        // Remove previous highlights
        item.classList.remove('highlight');
        listItem.style.display = '';

        // Highlight items matching the query
        if (item.textContent.toLowerCase().includes(query)) {
            item.classList.add('highlight');

            // Ensure all ancestors are visible
            let ancestor = listItem;
            while (ancestor) {
                ancestor.style.display = '';
                ancestor = ancestor.closest('ul')?.closest('li');
            }
        } else if (parentSpan && parentSpan.classList.contains('folder')) {
            // Check if the parent directory matches the query
            if (parentSpan.textContent.toLowerCase().includes(query)) {
                listItem.style.display = '';
            } else {
                listItem.style.display = 'none';
            }
        } else {
            // Default: Hide non-matching items
            listItem.style.display = 'none';
        }
    });
}

function resetTree() {
    const items = document.querySelectorAll('#tree span');
    items.forEach(item => {
        const listItem = item.closest('li');
        item.classList.remove('highlight');
        listItem.style.display = '';
    });
}

function expandAll() {
    const items = document.querySelectorAll('.folder + ul');
    items.forEach(item => item.classList.remove('hidden'));
}

function collapseAll() {
    const items = document.querySelectorAll('.folder + ul');
    items.forEach(item => item.classList.add('hidden'));
}

document.addEventListener('click', function (e) {
    if (e.target.classList.contains('folder')) {
        const sibling = e.target.nextElementSibling;
        if (sibling) {
            sibling.classList.toggle('hidden');
        }
    }
});

