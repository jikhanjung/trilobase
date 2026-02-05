/**
 * Trilobase Web Interface
 * Frontend JavaScript for taxonomy tree and genus browsing
 */

// State
let selectedFamilyId = null;
let genusModal = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    genusModal = new bootstrap.Modal(document.getElementById('genusModal'));
    loadTree();
});

/**
 * Load taxonomy tree from API
 */
async function loadTree() {
    const container = document.getElementById('tree-container');

    try {
        const response = await fetch('/api/tree');
        const tree = await response.json();
        container.innerHTML = '';

        tree.forEach(node => {
            container.appendChild(createTreeNode(node));
        });
    } catch (error) {
        container.innerHTML = `<div class="text-danger">Error loading tree: ${error.message}</div>`;
    }
}

/**
 * Create tree node element recursively
 */
function createTreeNode(node) {
    const div = document.createElement('div');
    div.className = 'tree-node';

    const hasChildren = node.children && node.children.length > 0;
    const isFamily = node.rank === 'Family';

    // Node content
    const content = document.createElement('div');
    content.className = `tree-node-content rank-${node.rank}`;
    content.dataset.id = node.id;
    content.dataset.rank = node.rank;
    content.dataset.name = node.name;

    // Toggle icon
    const toggle = document.createElement('span');
    toggle.className = 'tree-toggle';
    if (hasChildren) {
        toggle.innerHTML = '<i class="bi bi-chevron-down"></i>';
    }
    content.appendChild(toggle);

    // Folder/File icon
    const icon = document.createElement('span');
    icon.className = 'tree-icon';
    if (isFamily) {
        icon.innerHTML = '<i class="bi bi-folder-fill"></i>';
    } else {
        icon.innerHTML = '<i class="bi bi-folder2"></i>';
    }
    content.appendChild(icon);

    // Label
    const label = document.createElement('span');
    label.className = 'tree-label';
    label.textContent = node.name;
    content.appendChild(label);

    // Count (for families)
    if (isFamily && node.genera_count > 0) {
        const count = document.createElement('span');
        count.className = 'tree-count';
        count.textContent = `(${node.genera_count})`;
        content.appendChild(count);
    }

    // Click handler
    content.addEventListener('click', (e) => {
        if (hasChildren) {
            // Toggle children visibility
            const children = div.querySelector('.tree-children');
            if (children) {
                children.classList.toggle('collapsed');
                const chevron = toggle.querySelector('i');
                chevron.className = children.classList.contains('collapsed')
                    ? 'bi bi-chevron-right'
                    : 'bi bi-chevron-down';
            }
        }

        if (isFamily) {
            selectFamily(node.id, node.name);
        }
    });

    div.appendChild(content);

    // Children container
    if (hasChildren) {
        const childrenDiv = document.createElement('div');
        childrenDiv.className = 'tree-children';

        node.children.forEach(child => {
            childrenDiv.appendChild(createTreeNode(child));
        });

        div.appendChild(childrenDiv);
    }

    return div;
}

/**
 * Select a family and load its genera
 */
async function selectFamily(familyId, familyName) {
    // Update selection highlight
    document.querySelectorAll('.tree-node-content.selected').forEach(el => {
        el.classList.remove('selected');
    });
    document.querySelector(`.tree-node-content[data-id="${familyId}"]`)?.classList.add('selected');

    selectedFamilyId = familyId;

    // Update header
    const header = document.getElementById('list-header');
    header.innerHTML = `<h5><i class="bi bi-folder-fill"></i> ${familyName}</h5>`;

    // Load genera
    const container = document.getElementById('list-container');
    container.innerHTML = '<div class="loading">Loading genera...</div>';

    try {
        const response = await fetch(`/api/family/${familyId}/genera`);
        const data = await response.json();

        if (data.genera.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>No genera found in this family</p>
                </div>`;
            return;
        }

        // Build table
        let html = `
            <table class="genus-table">
                <thead>
                    <tr>
                        <th>Genus</th>
                        <th>Author</th>
                        <th>Year</th>
                        <th>Type Species</th>
                        <th>Location</th>
                    </tr>
                </thead>
                <tbody>`;

        data.genera.forEach(g => {
            const rowClass = g.is_valid ? '' : 'invalid';
            html += `
                <tr class="${rowClass}" onclick="showGenusDetail(${g.id})">
                    <td class="genus-name"><i>${g.name}</i></td>
                    <td>${g.author || ''}</td>
                    <td>${g.year || ''}</td>
                    <td>${truncate(g.type_species, 40)}</td>
                    <td>${truncate(g.location, 30)}</td>
                </tr>`;
        });

        html += '</tbody></table>';
        container.innerHTML = html;

    } catch (error) {
        container.innerHTML = `<div class="text-danger">Error loading genera: ${error.message}</div>`;
    }
}

/**
 * Show genus detail modal
 */
async function showGenusDetail(genusId) {
    const modalBody = document.getElementById('genusModalBody');
    const modalTitle = document.getElementById('genusModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    genusModal.show();

    try {
        const response = await fetch(`/api/genus/${genusId}`);
        const g = await response.json();

        modalTitle.innerHTML = `<i>${g.name}</i> ${g.author || ''}, ${g.year || ''}`;

        let html = '';

        // Basic Info
        html += `
            <div class="detail-section">
                <h6>Basic Information</h6>
                <div class="detail-grid">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value"><i>${g.name}</i></span>

                    <span class="detail-label">Author:</span>
                    <span class="detail-value">${g.author || '-'}</span>

                    <span class="detail-label">Year:</span>
                    <span class="detail-value">${g.year || '-'}${g.year_suffix || ''}</span>

                    <span class="detail-label">Family:</span>
                    <span class="detail-value">${g.family_name || g.family || '-'}</span>

                    <span class="detail-label">Status:</span>
                    <span class="detail-value ${g.is_valid ? '' : 'invalid'}">
                        ${g.is_valid ? 'Valid' : 'Invalid'}
                    </span>

                    <span class="detail-label">Temporal Range:</span>
                    <span class="detail-value">${g.temporal_code || '-'}</span>
                </div>
            </div>`;

        // Type Species
        if (g.type_species) {
            html += `
                <div class="detail-section">
                    <h6>Type Species</h6>
                    <div class="detail-grid">
                        <span class="detail-label">Species:</span>
                        <span class="detail-value"><i>${g.type_species}</i></span>

                        <span class="detail-label">Author:</span>
                        <span class="detail-value">${g.type_species_author || '-'}</span>
                    </div>
                </div>`;
        }

        // Geographic Info
        html += `
            <div class="detail-section">
                <h6>Geographic Information</h6>
                <div class="detail-grid">
                    <span class="detail-label">Formation:</span>
                    <span class="detail-value">${g.formation || '-'}</span>

                    <span class="detail-label">Location:</span>
                    <span class="detail-value">${g.location || '-'}</span>
                </div>`;

        // Locations from relation table
        if (g.locations && g.locations.length > 0) {
            html += `
                <div class="mt-2">
                    <span class="detail-label">Countries:</span>
                    <ul class="mb-0">`;
            g.locations.forEach(l => {
                html += `<li>${l.country}${l.region ? ' (' + l.region + ')' : ''}</li>`;
            });
            html += '</ul></div>';
        }
        html += '</div>';

        // Synonyms
        if (g.synonyms && g.synonyms.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Synonymy</h6>
                    <ul class="list-unstyled">`;
            g.synonyms.forEach(s => {
                html += `
                    <li>
                        <span class="badge bg-secondary badge-synonym">${s.synonym_type}</span>
                        <i>${s.senior_name}</i>
                        ${s.fide_author ? `<small class="text-muted">fide ${s.fide_author}${s.fide_year ? ', ' + s.fide_year : ''}</small>` : ''}
                    </li>`;
            });
            html += '</ul></div>';
        }

        // Notes
        if (g.notes) {
            html += `
                <div class="detail-section">
                    <h6>Notes</h6>
                    <p>${g.notes}</p>
                </div>`;
        }

        // Raw Entry
        if (g.raw_entry) {
            html += `
                <div class="detail-section">
                    <h6>Original Entry</h6>
                    <div class="raw-entry">${g.raw_entry}</div>
                </div>`;
        }

        modalBody.innerHTML = html;

    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error loading genus: ${error.message}</div>`;
    }
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}
