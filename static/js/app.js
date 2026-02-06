/**
 * Trilobase Web Interface
 * Frontend JavaScript for taxonomy tree and genus browsing
 */

// State
let selectedFamilyId = null;
let genusModal = null;
let currentGenera = [];  // Store current genera for filtering
let showOnlyValid = true;  // Filter state

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

    // Info icon
    const infoBtn = document.createElement('span');
    infoBtn.className = 'tree-info';
    infoBtn.innerHTML = '<i class="bi bi-info-circle"></i>';
    infoBtn.title = 'View details';
    infoBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        showRankDetail(node.id, node.name, node.rank);
    });
    content.appendChild(infoBtn);

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

    // Update header with filter checkbox
    const header = document.getElementById('list-header');
    header.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="bi bi-folder-fill"></i> ${familyName}</h5>
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="validOnlyCheck"
                       ${showOnlyValid ? 'checked' : ''} onchange="toggleValidFilter()">
                <label class="form-check-label" for="validOnlyCheck">Valid only</label>
            </div>
        </div>`;

    // Load genera
    const container = document.getElementById('list-container');
    container.innerHTML = '<div class="loading">Loading genera...</div>';

    try {
        const response = await fetch(`/api/family/${familyId}/genera`);
        const data = await response.json();

        currentGenera = data.genera;  // Store for filtering
        renderGeneraTable();

    } catch (error) {
        container.innerHTML = `<div class="text-danger">Error loading genera: ${error.message}</div>`;
    }
}

/**
 * Toggle valid-only filter
 */
function toggleValidFilter() {
    showOnlyValid = document.getElementById('validOnlyCheck').checked;
    renderGeneraTable();
}

/**
 * Render genera table with current filter
 */
function renderGeneraTable() {
    const container = document.getElementById('list-container');

    const genera = showOnlyValid
        ? currentGenera.filter(g => g.is_valid)
        : currentGenera;

    if (genera.length === 0) {
        const message = showOnlyValid && currentGenera.length > 0
            ? `No valid genera (${currentGenera.length} invalid)`
            : 'No genera found in this family';
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-inbox"></i>
                <p>${message}</p>
            </div>`;
        return;
    }

    // Count stats
    const validCount = currentGenera.filter(g => g.is_valid).length;
    const invalidCount = currentGenera.length - validCount;
    const statsText = showOnlyValid
        ? `Showing ${validCount} valid genera` + (invalidCount > 0 ? ` (${invalidCount} invalid hidden)` : '')
        : `Showing all ${currentGenera.length} genera (${validCount} valid, ${invalidCount} invalid)`;

    let html = `<div class="genera-stats text-muted mb-2">${statsText}</div>`;
    html += `
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

    genera.forEach(g => {
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
                const seniorLink = s.senior_taxon_id
                    ? `<a href="#" class="synonym-link" onclick="showGenusDetail(${s.senior_taxon_id}); return false;"><i>${s.senior_name}</i></a>`
                    : `<i>${s.senior_name}</i>`;
                html += `
                    <li>
                        <span class="badge bg-secondary badge-synonym">${s.synonym_type}</span>
                        ${seniorLink}
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
 * Show rank detail modal (Class, Order, Suborder, Superfamily, Family)
 */
async function showRankDetail(rankId, rankName, rankType) {
    const modalBody = document.getElementById('genusModalBody');
    const modalTitle = document.getElementById('genusModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    genusModal.show();

    try {
        const response = await fetch(`/api/rank/${rankId}`);
        const r = await response.json();

        modalTitle.innerHTML = `<span class="badge bg-secondary me-2">${r.rank}</span> ${r.name}`;

        let html = '';

        // Basic Info
        html += `
            <div class="detail-section">
                <h6>Basic Information</h6>
                <div class="detail-grid">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value">${r.name}</span>

                    <span class="detail-label">Rank:</span>
                    <span class="detail-value">${r.rank}</span>

                    <span class="detail-label">Author:</span>
                    <span class="detail-value">${r.author || '-'}</span>

                    <span class="detail-label">Year:</span>
                    <span class="detail-value">${r.year || '-'}</span>

                    <span class="detail-label">Parent:</span>
                    <span class="detail-value">${r.parent_name ? r.parent_name + ' (' + r.parent_rank + ')' : '-'}</span>
                </div>
            </div>`;

        // Statistics
        if (r.genera_count || r.children_counts.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Statistics</h6>
                    <div class="detail-grid">`;

            if (r.genera_count) {
                html += `
                    <span class="detail-label">Genera:</span>
                    <span class="detail-value">${r.genera_count}</span>`;
            }

            r.children_counts.forEach(c => {
                // Skip Genus count if genera_count already shown
                if (c.rank === 'Genus' && r.genera_count) return;
                html += `
                    <span class="detail-label">${c.rank}:</span>
                    <span class="detail-value">${c.count}</span>`;
            });

            html += '</div></div>';
        }

        // Children list
        if (r.children && r.children.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Children (${r.children.length}${r.children.length >= 20 ? '+' : ''})</h6>
                    <ul class="list-unstyled children-list">`;

            r.children.forEach(c => {
                if (c.rank === 'Genus') {
                    html += `
                    <li class="clickable" onclick="navigateToGenus(${c.id}, ${r.id}, '${r.name.replace(/'/g, "\\'")}')">
                        <span class="badge bg-light text-dark me-1">${c.rank}</span>
                        <strong><i>${c.name}</i></strong>
                        ${c.author ? '<small class="text-muted">' + c.author + '</small>' : ''}
                    </li>`;
                } else {
                    html += `
                    <li class="clickable" onclick="navigateToRank(${c.id}, '${c.name.replace(/'/g, "\\'")}', '${c.rank}')">
                        <span class="badge bg-light text-dark me-1">${c.rank}</span>
                        <strong>${c.name}</strong>
                        ${c.author ? '<small class="text-muted">' + c.author + '</small>' : ''}
                    </li>`;
                }
            });

            html += '</ul></div>';
        }

        // Notes
        if (r.notes) {
            html += `
                <div class="detail-section">
                    <h6>Notes</h6>
                    <p>${r.notes}</p>
                </div>`;
        }

        modalBody.innerHTML = html;

    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error loading details: ${error.message}</div>`;
    }
}

/**
 * Expand tree path to a specific node and highlight it
 */
function expandTreeToNode(nodeId) {
    const nodeContent = document.querySelector(`.tree-node-content[data-id="${nodeId}"]`);
    if (!nodeContent) return;

    // Walk up DOM to expand all collapsed parent containers
    let element = nodeContent.parentElement;
    while (element) {
        if (element.classList && element.classList.contains('tree-children') && element.classList.contains('collapsed')) {
            element.classList.remove('collapsed');
            const parentContent = element.previousElementSibling;
            if (parentContent) {
                const chevron = parentContent.querySelector('.tree-toggle i');
                if (chevron) chevron.className = 'bi bi-chevron-down';
            }
        }
        element = element.parentElement;
    }

    // Highlight the node
    document.querySelectorAll('.tree-node-content.selected').forEach(el => {
        el.classList.remove('selected');
    });
    nodeContent.classList.add('selected');
    nodeContent.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/**
 * Navigate to a non-Genus rank from children list
 */
function navigateToRank(rankId, rankName, rankType) {
    expandTreeToNode(rankId);
    if (rankType === 'Family') {
        selectFamily(rankId, rankName);
    }
    showRankDetail(rankId, rankName, rankType);
}

/**
 * Navigate to a Genus from children list
 */
function navigateToGenus(genusId, familyId, familyName) {
    expandTreeToNode(familyId);
    selectFamily(familyId, familyName);
    showGenusDetail(genusId);
}

/**
 * Expand all tree nodes
 */
function expandAll() {
    document.querySelectorAll('.tree-children.collapsed').forEach(el => {
        el.classList.remove('collapsed');
    });
    document.querySelectorAll('.tree-toggle i').forEach(el => {
        el.className = 'bi bi-chevron-down';
    });
}

/**
 * Collapse all tree nodes
 */
function collapseAll() {
    document.querySelectorAll('.tree-children').forEach(el => {
        el.classList.add('collapsed');
    });
    document.querySelectorAll('.tree-toggle i').forEach(el => {
        el.className = 'bi bi-chevron-right';
    });
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}
