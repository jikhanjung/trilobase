/**
 * Trilobase Web Interface
 * Frontend JavaScript for taxonomy tree and genus browsing
 */

// State
let selectedFamilyId = null;
let genusModal = null;
let currentGenera = [];  // Store current genera for filtering
let showOnlyValid = true;  // Filter state

// Manifest state
let manifest = null;
let currentView = 'taxonomy_tree';
let tableViewData = [];
let tableViewSort = null;
let tableViewSearchTerm = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    genusModal = new bootstrap.Modal(document.getElementById('genusModal'));
    loadManifest();
    loadTree();
});

/**
 * Load UI manifest from API (graceful degradation if unavailable)
 */
async function loadManifest() {
    try {
        const response = await fetch('/api/manifest');
        if (!response.ok) return;
        const data = await response.json();
        manifest = data.manifest;
        buildViewTabs();
    } catch (error) {
        // Graceful degradation: manifest unavailable, use existing UI
    }
}

/**
 * Build view tabs from manifest
 */
function buildViewTabs() {
    if (!manifest || !manifest.views) return;

    const tabsContainer = document.getElementById('view-tabs');
    let html = '';

    for (const [key, view] of Object.entries(manifest.views)) {
        // Skip detail type views (they're not top-level tabs)
        if (view.type === 'detail') continue;

        const isActive = key === currentView;
        const icon = view.icon || 'bi-square';
        html += `<button class="view-tab ${isActive ? 'active' : ''}"
                         data-view="${key}" onclick="switchToView('${key}')">
                    <i class="bi ${icon}"></i> ${view.title}
                 </button>`;
    }

    tabsContainer.innerHTML = html;
}

/**
 * Switch between views
 */
function switchToView(viewKey) {
    if (!manifest || !manifest.views[viewKey]) return;

    currentView = viewKey;
    const view = manifest.views[viewKey];

    // Update tab active state
    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === viewKey);
    });

    // Show/hide view containers
    const treeContainer = document.getElementById('view-tree');
    const tableContainer = document.getElementById('view-table');

    if (view.type === 'tree') {
        treeContainer.style.display = '';
        tableContainer.style.display = 'none';
    } else if (view.type === 'table') {
        treeContainer.style.display = 'none';
        tableContainer.style.display = '';
        tableViewSort = view.default_sort || null;
        tableViewSearchTerm = '';
        renderTableView(viewKey);
    }
}

/**
 * Render a table view using manifest definition and query execution
 */
async function renderTableView(viewKey) {
    const view = manifest.views[viewKey];
    if (!view || view.type !== 'table') return;

    const header = document.getElementById('table-view-header');
    const toolbar = document.getElementById('table-view-toolbar');
    const body = document.getElementById('table-view-body');

    // Header
    header.innerHTML = `<h5><i class="bi ${view.icon || 'bi-table'}"></i> ${view.title}</h5>
                        <p class="text-muted mb-0">${view.description || ''}</p>`;

    // Toolbar (search)
    if (view.searchable) {
        toolbar.innerHTML = `<div class="table-view-search">
            <i class="bi bi-search"></i>
            <input type="text" class="form-control form-control-sm"
                   placeholder="Search..." id="table-search-input"
                   oninput="onTableSearch(this.value)" value="${tableViewSearchTerm}">
        </div>`;
    } else {
        toolbar.innerHTML = '';
    }

    // Load data
    body.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const response = await fetch(`/api/queries/${view.source_query}/execute`);
        if (!response.ok) {
            body.innerHTML = '<div class="text-danger">Error loading data</div>';
            return;
        }
        const data = await response.json();
        tableViewData = data.rows;
        renderTableViewRows(viewKey);
    } catch (error) {
        body.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

/**
 * Render table rows with current sort and search applied
 */
function renderTableViewRows(viewKey) {
    const view = manifest.views[viewKey];
    if (!view || !view.columns) return;

    const body = document.getElementById('table-view-body');
    let rows = [...tableViewData];

    // Apply search
    if (tableViewSearchTerm) {
        const term = tableViewSearchTerm.toLowerCase();
        const searchableCols = view.columns.filter(c => c.searchable).map(c => c.key);
        rows = rows.filter(row =>
            searchableCols.some(key => {
                const val = row[key];
                return val && String(val).toLowerCase().includes(term);
            })
        );
    }

    // Apply sort
    if (tableViewSort) {
        const { key, direction } = tableViewSort;
        rows.sort((a, b) => {
            let va = a[key], vb = b[key];
            if (va == null) va = '';
            if (vb == null) vb = '';
            if (typeof va === 'number' && typeof vb === 'number') {
                return direction === 'asc' ? va - vb : vb - va;
            }
            va = String(va).toLowerCase();
            vb = String(vb).toLowerCase();
            if (va < vb) return direction === 'asc' ? -1 : 1;
            if (va > vb) return direction === 'asc' ? 1 : -1;
            return 0;
        });
    }

    // Build table
    let html = `<div class="table-view-stats text-muted mb-2">${rows.length} of ${tableViewData.length} records</div>`;
    html += '<table class="manifest-table"><thead><tr>';

    view.columns.forEach(col => {
        const sortIcon = getSortIcon(col.key);
        const sortable = col.sortable ? `onclick="onTableSort('${viewKey}', '${col.key}')"` : '';
        const sortableClass = col.sortable ? 'sortable' : '';
        html += `<th class="${sortableClass}" ${sortable}>${col.label} ${sortIcon}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Click handlers per view
    const clickHandlers = {
        'countries_table': (row) => `onclick="showCountryDetail(${row.id})"`,
        'formations_table': (row) => `onclick="showFormationDetail(${row.id})"`,
        'references_table': (row) => `onclick="showBibliographyDetail(${row.id})"`,
        'genera_table': (row) => `onclick="showGenusDetail(${row.id})"`,
        'chronostratigraphy_table': (row) => `onclick="showChronostratDetail(${row.id})"`,
    };
    const getClick = clickHandlers[viewKey];

    if (rows.length === 0) {
        html += `<tr><td colspan="${view.columns.length}" class="text-center text-muted py-4">No matching records</td></tr>`;
    } else {
        rows.forEach(row => {
            const clickAttr = getClick ? getClick(row) : '';
            html += `<tr ${clickAttr}>`;
            view.columns.forEach(col => {
                let val = row[col.key];
                if (col.type === 'color') {
                    const color = val || '';
                    val = color ? `<span class="color-chip" style="background-color:${color}" title="${color}"></span> ${color}` : '';
                } else if (col.type === 'boolean') {
                    val = val ? 'Yes' : 'No';
                } else if (val == null) {
                    val = '';
                }
                const italic = col.italic ? `<i>${val}</i>` : val;
                html += `<td>${italic}</td>`;
            });
            html += '</tr>';
        });
    }

    html += '</tbody></table>';
    body.innerHTML = html;
}

/**
 * Get sort indicator icon for a column
 */
function getSortIcon(key) {
    if (!tableViewSort || tableViewSort.key !== key) return '';
    return tableViewSort.direction === 'asc'
        ? '<i class="bi bi-caret-up-fill"></i>'
        : '<i class="bi bi-caret-down-fill"></i>';
}

/**
 * Handle table column sort click
 */
function onTableSort(viewKey, key) {
    if (tableViewSort && tableViewSort.key === key) {
        tableViewSort.direction = tableViewSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        tableViewSort = { key, direction: 'asc' };
    }
    renderTableViewRows(viewKey);
}

/**
 * Handle table search input
 */
function onTableSearch(value) {
    tableViewSearchTerm = value;
    renderTableViewRows(currentView);
}

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

                    <span class="detail-label">Classification:</span>
                    <span class="detail-value">${buildHierarchyHTML(g)}</span>

                    <span class="detail-label">Status:</span>
                    <span class="detail-value ${g.is_valid ? '' : 'invalid'}">
                        ${g.is_valid ? 'Valid' : 'Invalid'}
                    </span>

                    <span class="detail-label">Temporal Range:</span>
                    <span class="detail-value">${buildTemporalRangeHTML(g)}</span>
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
        {
            let geoGridHtml = '';

            // Country/Location: relation data first, raw fallback
            if (g.locations && g.locations.length > 0) {
                const locLinks = g.locations.map(l => {
                    let link = `<a class="detail-link" onclick="showCountryDetail(${l.country_id})">${l.country_name}</a>`;
                    if (l.region_id && l.region_name) {
                        link += ` &gt; <a class="detail-link" onclick="showRegionDetail(${l.region_id})">${l.region_name}</a>`;
                    }
                    return link;
                }).join(', ');
                geoGridHtml += `
                    <span class="detail-label">Country:</span>
                    <span class="detail-value">${locLinks}</span>`;
            } else if (g.location) {
                geoGridHtml += `
                    <span class="detail-label">Location:</span>
                    <span class="detail-value">${g.location}</span>`;
            }

            // Formation: relation data first, raw fallback
            if (g.formations && g.formations.length > 0) {
                const fmtLinks = g.formations.map(f =>
                    `<a class="detail-link" onclick="showFormationDetail(${f.id})">${f.name}</a>${f.period ? ' (' + f.period + ')' : ''}`
                ).join(', ');
                geoGridHtml += `
                    <span class="detail-label">Formation:</span>
                    <span class="detail-value">${fmtLinks}</span>`;
            } else if (g.formation) {
                geoGridHtml += `
                    <span class="detail-label">Formation:</span>
                    <span class="detail-value">${g.formation}</span>`;
            }

            if (geoGridHtml) {
                html += `
                    <div class="detail-section">
                        <h6>Geographic Information</h6>
                        <div class="detail-grid">${geoGridHtml}
                        </div>
                    </div>`;
            }
        }

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

        // My Notes section
        html += buildAnnotationSectionHTML('genus', g.id);

        modalBody.innerHTML = html;

        // Load annotations after DOM is ready
        loadAnnotations('genus', g.id);

    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error loading genus: ${error.message}</div>`;
    }
}

/**
 * Show country detail modal
 */
async function showCountryDetail(countryId) {
    const modalBody = document.getElementById('genusModalBody');
    const modalTitle = document.getElementById('genusModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    genusModal.show();

    try {
        const response = await fetch(`/api/country/${countryId}`);
        const c = await response.json();

        modalTitle.innerHTML = `<i class="bi bi-geo-alt"></i> ${c.name}`;

        let html = '';

        // Basic Info
        html += `
            <div class="detail-section">
                <h6>Basic Information</h6>
                <div class="detail-grid">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value">${c.name}</span>

                    <span class="detail-label">COW Code:</span>
                    <span class="detail-value">${c.cow_ccode || '-'}</span>

                    <span class="detail-label">Taxa Count:</span>
                    <span class="detail-value">${c.taxa_count || 0}</span>
                </div>
            </div>`;

        // Regions list
        if (c.regions && c.regions.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Regions (${c.regions.length})</h6>
                    <div class="genera-list">
                        <table class="manifest-table">
                            <thead><tr>
                                <th>Region</th><th>Taxa Count</th>
                            </tr></thead><tbody>`;
            c.regions.forEach(r => {
                html += `<tr onclick="showRegionDetail(${r.id})">
                    <td>${r.name}</td>
                    <td>${r.taxa_count || 0}</td>
                </tr>`;
            });
            html += '</tbody></table></div></div>';
        }

        // Genera list
        if (c.genera && c.genera.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Genera (${c.genera.length})</h6>
                    <div class="genera-list">
                        <table class="manifest-table">
                            <thead><tr>
                                <th>Genus</th><th>Author</th><th>Year</th><th>Region</th><th>Valid</th>
                            </tr></thead><tbody>`;
            c.genera.forEach(g => {
                const regionLink = g.region_id
                    ? `<a class="detail-link" onclick="event.stopPropagation(); showRegionDetail(${g.region_id})">${g.region || ''}</a>`
                    : (g.region || '');
                html += `<tr onclick="showGenusDetail(${g.id})">
                    <td><i>${g.name}</i></td>
                    <td>${g.author || ''}</td>
                    <td>${g.year || ''}</td>
                    <td>${regionLink}</td>
                    <td>${g.is_valid ? 'Yes' : 'No'}</td>
                </tr>`;
            });
            html += '</tbody></table></div></div>';
        }

        modalBody.innerHTML = html;
    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

/**
 * Show chronostratigraphic unit detail modal
 */
async function showChronostratDetail(icsId) {
    const modalBody = document.getElementById('genusModalBody');
    const modalTitle = document.getElementById('genusModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    genusModal.show();

    try {
        const response = await fetch(`/api/chronostrat/${icsId}`);
        const c = await response.json();

        modalTitle.innerHTML = `<i class="bi bi-clock-history"></i> ${c.name}`;

        let html = '';

        // Basic Info
        const timeRange = (c.start_mya != null && c.end_mya != null)
            ? `${c.start_mya} — ${c.end_mya} Ma` : '-';
        const gssp = c.ratified_gssp ? 'Yes' : 'No';

        html += `
            <div class="detail-section">
                <h6>Basic Information</h6>
                <div class="detail-grid">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value">${c.name}</span>

                    <span class="detail-label">Rank:</span>
                    <span class="detail-value">${c.rank}</span>

                    <span class="detail-label">Time Range:</span>
                    <span class="detail-value">${timeRange}</span>

                    <span class="detail-label">Short Code:</span>
                    <span class="detail-value">${c.short_code || '-'}</span>

                    <span class="detail-label">Color:</span>
                    <span class="detail-value">${c.color ? `<span class="color-chip" style="background-color:${c.color}"></span> ${c.color}` : '-'}</span>

                    <span class="detail-label">Ratified GSSP:</span>
                    <span class="detail-value">${gssp}</span>
                </div>
            </div>`;

        // Hierarchy (parent)
        if (c.parent) {
            html += `
                <div class="detail-section">
                    <h6>Hierarchy</h6>
                    <div class="detail-grid">
                        <span class="detail-label">Parent:</span>
                        <span class="detail-value">
                            <a class="detail-link" onclick="showChronostratDetail(${c.parent.id})">${c.parent.name}</a>
                            <small class="text-muted">(${c.parent.rank})</small>
                        </span>
                    </div>
                </div>`;
        }

        // Children
        if (c.children && c.children.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Children (${c.children.length})</h6>
                    <div class="genera-list">
                        <table class="manifest-table">
                            <thead><tr>
                                <th>Name</th><th>Rank</th><th>Time Range</th><th>Color</th>
                            </tr></thead><tbody>`;
            c.children.forEach(ch => {
                const chRange = (ch.start_mya != null && ch.end_mya != null)
                    ? `${ch.start_mya} — ${ch.end_mya} Ma` : '-';
                const colorChip = ch.color ? `<span class="color-chip" style="background-color:${ch.color}"></span>` : '';
                html += `<tr onclick="showChronostratDetail(${ch.id})">
                    <td>${ch.name}</td>
                    <td>${ch.rank}</td>
                    <td>${chRange}</td>
                    <td>${colorChip} ${ch.color || ''}</td>
                </tr>`;
            });
            html += '</tbody></table></div></div>';
        }

        // Mapped Temporal Codes
        if (c.mappings && c.mappings.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Mapped Temporal Codes</h6>
                    <ul class="list-unstyled">`;
            c.mappings.forEach(m => {
                html += `<li>
                    <code>${m.temporal_code}</code>
                    <small class="text-muted ms-1">(${m.mapping_type})</small>
                </li>`;
            });
            html += '</ul></div>';
        }

        // Related Genera
        if (c.genera && c.genera.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Related Genera (${c.genera.length})</h6>
                    <div class="genera-list">
                        <table class="manifest-table">
                            <thead><tr>
                                <th>Genus</th><th>Author</th><th>Year</th><th>Temporal Code</th><th>Valid</th>
                            </tr></thead><tbody>`;
            c.genera.forEach(g => {
                html += `<tr onclick="showGenusDetail(${g.id})">
                    <td><i>${g.name}</i></td>
                    <td>${g.author || ''}</td>
                    <td>${g.year || ''}</td>
                    <td><code>${g.temporal_code || ''}</code></td>
                    <td>${g.is_valid ? 'Yes' : 'No'}</td>
                </tr>`;
            });
            html += '</tbody></table></div></div>';
        }

        modalBody.innerHTML = html;
    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

/**
 * Show region detail modal
 */
async function showRegionDetail(regionId) {
    const modalBody = document.getElementById('genusModalBody');
    const modalTitle = document.getElementById('genusModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    genusModal.show();

    try {
        const response = await fetch(`/api/region/${regionId}`);
        const r = await response.json();

        modalTitle.innerHTML = `<i class="bi bi-geo-alt"></i> ${r.name}`;

        let html = '';

        // Basic Info
        html += `
            <div class="detail-section">
                <h6>Basic Information</h6>
                <div class="detail-grid">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value">${r.name}</span>

                    <span class="detail-label">Country:</span>
                    <span class="detail-value"><a class="detail-link" onclick="showCountryDetail(${r.parent.id})">${r.parent.name}</a></span>

                    <span class="detail-label">Taxa Count:</span>
                    <span class="detail-value">${r.taxa_count || 0}</span>
                </div>
            </div>`;

        // Genera list
        if (r.genera && r.genera.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Genera (${r.genera.length})</h6>
                    <div class="genera-list">
                        <table class="manifest-table">
                            <thead><tr>
                                <th>Genus</th><th>Author</th><th>Year</th><th>Valid</th>
                            </tr></thead><tbody>`;
            r.genera.forEach(g => {
                html += `<tr onclick="showGenusDetail(${g.id})">
                    <td><i>${g.name}</i></td>
                    <td>${g.author || ''}</td>
                    <td>${g.year || ''}</td>
                    <td>${g.is_valid ? 'Yes' : 'No'}</td>
                </tr>`;
            });
            html += '</tbody></table></div></div>';
        }

        modalBody.innerHTML = html;
    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

/**
 * Show formation detail modal
 */
async function showFormationDetail(formationId) {
    const modalBody = document.getElementById('genusModalBody');
    const modalTitle = document.getElementById('genusModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    genusModal.show();

    try {
        const response = await fetch(`/api/formation/${formationId}`);
        const f = await response.json();

        modalTitle.innerHTML = `<i class="bi bi-layers"></i> ${f.name}`;

        let html = '';

        // Basic Info
        html += `
            <div class="detail-section">
                <h6>Basic Information</h6>
                <div class="detail-grid">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value">${f.name}</span>

                    <span class="detail-label">Type:</span>
                    <span class="detail-value">${f.formation_type || '-'}</span>

                    <span class="detail-label">Country:</span>
                    <span class="detail-value">${f.country || '-'}</span>

                    <span class="detail-label">Region:</span>
                    <span class="detail-value">${f.region || '-'}</span>

                    <span class="detail-label">Period:</span>
                    <span class="detail-value">${f.period || '-'}</span>

                    <span class="detail-label">Taxa Count:</span>
                    <span class="detail-value">${f.taxa_count || 0}</span>
                </div>
            </div>`;

        // Genera list
        if (f.genera && f.genera.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Genera (${f.genera.length})</h6>
                    <div class="genera-list">
                        <table class="manifest-table">
                            <thead><tr>
                                <th>Genus</th><th>Author</th><th>Year</th><th>Valid</th>
                            </tr></thead><tbody>`;
            f.genera.forEach(g => {
                html += `<tr onclick="showGenusDetail(${g.id})">
                    <td><i>${g.name}</i></td>
                    <td>${g.author || ''}</td>
                    <td>${g.year || ''}</td>
                    <td>${g.is_valid ? 'Yes' : 'No'}</td>
                </tr>`;
            });
            html += '</tbody></table></div></div>';
        }

        modalBody.innerHTML = html;
    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

/**
 * Show bibliography detail modal
 */
async function showBibliographyDetail(bibId) {
    const modalBody = document.getElementById('genusModalBody');
    const modalTitle = document.getElementById('genusModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    genusModal.show();

    try {
        const response = await fetch(`/api/bibliography/${bibId}`);
        const b = await response.json();

        modalTitle.innerHTML = `<i class="bi bi-book"></i> ${b.authors || 'Unknown'}, ${b.year || ''}`;

        let html = '';

        // Basic Info
        html += `
            <div class="detail-section">
                <h6>Basic Information</h6>
                <div class="detail-grid">
                    <span class="detail-label">Authors:</span>
                    <span class="detail-value">${b.authors || '-'}</span>

                    <span class="detail-label">Year:</span>
                    <span class="detail-value">${b.year || '-'}${b.year_suffix || ''}</span>

                    <span class="detail-label">Title:</span>
                    <span class="detail-value">${b.title || '-'}</span>

                    <span class="detail-label">Journal:</span>
                    <span class="detail-value">${b.journal || '-'}</span>

                    <span class="detail-label">Volume:</span>
                    <span class="detail-value">${b.volume || '-'}</span>

                    <span class="detail-label">Pages:</span>
                    <span class="detail-value">${b.pages || '-'}</span>

                    <span class="detail-label">Type:</span>
                    <span class="detail-value">${b.reference_type || '-'}</span>`;

        if (b.publisher) {
            html += `
                    <span class="detail-label">Publisher:</span>
                    <span class="detail-value">${b.publisher}</span>`;
        }
        if (b.city) {
            html += `
                    <span class="detail-label">City:</span>
                    <span class="detail-value">${b.city}</span>`;
        }
        if (b.editors) {
            html += `
                    <span class="detail-label">Editors:</span>
                    <span class="detail-value">${b.editors}</span>`;
        }
        if (b.book_title) {
            html += `
                    <span class="detail-label">Book Title:</span>
                    <span class="detail-value">${b.book_title}</span>`;
        }

        html += '</div></div>';

        // Raw Entry
        if (b.raw_entry) {
            html += `
                <div class="detail-section">
                    <h6>Original Entry</h6>
                    <div class="raw-entry">${b.raw_entry}</div>
                </div>`;
        }

        // Related Genera
        if (b.genera && b.genera.length > 0) {
            html += `
                <div class="detail-section">
                    <h6>Related Genera (${b.genera.length})</h6>
                    <div class="genera-list">
                        <table class="manifest-table">
                            <thead><tr>
                                <th>Genus</th><th>Author</th><th>Year</th><th>Valid</th>
                            </tr></thead><tbody>`;
            b.genera.forEach(g => {
                html += `<tr onclick="showGenusDetail(${g.id})">
                    <td><i>${g.name}</i></td>
                    <td>${g.author || ''}</td>
                    <td>${g.year || ''}</td>
                    <td>${g.is_valid ? 'Yes' : 'No'}</td>
                </tr>`;
            });
            html += '</tbody></table></div></div>';
        } else {
            html += `
                <div class="detail-section">
                    <h6>Related Genera</h6>
                    <p class="text-muted">No matching genera found.</p>
                </div>`;
        }

        modalBody.innerHTML = html;
    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
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

        // My Notes section
        const entityType = r.rank.toLowerCase();
        html += buildAnnotationSectionHTML(entityType, r.id);

        modalBody.innerHTML = html;

        // Load annotations after DOM is ready
        loadAnnotations(entityType, r.id);

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
 * Build temporal range HTML with ICS mapping links
 */
function buildTemporalRangeHTML(g) {
    if (!g.temporal_code) return '-';
    let html = `<code>${g.temporal_code}</code>`;
    if (g.temporal_ics_mapping && g.temporal_ics_mapping.length > 0) {
        const links = g.temporal_ics_mapping.map(m =>
            `<a class="detail-link" onclick="showChronostratDetail(${m.id})">${m.name}</a>` +
            (m.mapping_type !== 'exact' ? ` <small class="text-muted">(${m.mapping_type})</small>` : '')
        ).join(', ');
        html += ` → ${links}`;
    }
    return html;
}

/**
 * Build hierarchy HTML for genus detail (Class → Order → ... → Family)
 */
function buildHierarchyHTML(g) {
    if (g.hierarchy && g.hierarchy.length > 0) {
        return g.hierarchy.map(h =>
            `<a class="detail-link" onclick="showRankDetail(${h.id}, '${h.name.replace(/'/g, "\\'")}', '${h.rank}')">${h.name}</a>` +
            ` <small class="text-muted">(${h.rank})</small>`
        ).join(' → ');
    }
    return g.family_name || g.family || '-';
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

/**
 * Build the static HTML for the annotation section (form + placeholder for list)
 */
function buildAnnotationSectionHTML(entityType, entityId) {
    return `
        <div class="annotation-section" id="annotation-section-${entityType}-${entityId}">
            <h6>My Notes</h6>
            <div id="annotation-list-${entityType}-${entityId}">
                <div class="loading">Loading notes...</div>
            </div>
            <div class="annotation-form mt-2">
                <div class="mb-2">
                    <select class="form-select form-select-sm" id="annotation-type-${entityType}-${entityId}">
                        <option value="note">Note</option>
                        <option value="correction">Correction</option>
                        <option value="alternative">Alternative</option>
                        <option value="link">Link</option>
                    </select>
                </div>
                <div class="mb-2">
                    <textarea class="form-control form-control-sm" id="annotation-content-${entityType}-${entityId}"
                              rows="2" placeholder="Add a note..."></textarea>
                </div>
                <div class="d-flex gap-2">
                    <input type="text" class="form-control form-control-sm" id="annotation-author-${entityType}-${entityId}"
                           placeholder="Author (optional)" style="max-width: 200px;">
                    <button class="btn btn-sm btn-outline-primary"
                            onclick="addAnnotation('${entityType}', ${entityId})">Add</button>
                </div>
            </div>
        </div>`;
}

/**
 * Load annotations for an entity and render them
 */
async function loadAnnotations(entityType, entityId) {
    const listContainer = document.getElementById(`annotation-list-${entityType}-${entityId}`);
    if (!listContainer) return;

    try {
        const response = await fetch(`/api/annotations/${entityType}/${entityId}`);
        const annotations = await response.json();

        if (annotations.length === 0) {
            listContainer.innerHTML = '<p class="text-muted mb-0" style="font-size:0.85rem;">No notes yet.</p>';
            return;
        }

        let html = '';
        annotations.forEach(a => {
            const typeBadge = {
                'note': 'bg-info',
                'correction': 'bg-warning text-dark',
                'alternative': 'bg-success',
                'link': 'bg-primary'
            }[a.annotation_type] || 'bg-secondary';

            html += `
                <div class="annotation-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <span class="badge ${typeBadge}" style="font-size:0.7rem;">${a.annotation_type}</span>
                            ${a.author ? `<small class="text-muted ms-1">${a.author}</small>` : ''}
                            <small class="text-muted ms-1">${a.created_at}</small>
                        </div>
                        <button class="btn btn-sm btn-outline-danger" style="padding:0 4px; font-size:0.7rem;"
                                onclick="deleteAnnotation(${a.id}, '${entityType}', ${entityId})">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                    <div style="margin-top:4px; font-size:0.9rem;">${a.content}</div>
                </div>`;
        });

        listContainer.innerHTML = html;
    } catch (error) {
        listContainer.innerHTML = `<div class="text-danger" style="font-size:0.85rem;">Error loading notes.</div>`;
    }
}

/**
 * Add a new annotation
 */
async function addAnnotation(entityType, entityId) {
    const contentEl = document.getElementById(`annotation-content-${entityType}-${entityId}`);
    const typeEl = document.getElementById(`annotation-type-${entityType}-${entityId}`);
    const authorEl = document.getElementById(`annotation-author-${entityType}-${entityId}`);

    const content = contentEl.value.trim();
    if (!content) return;

    try {
        const response = await fetch('/api/annotations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                entity_type: entityType,
                entity_id: entityId,
                annotation_type: typeEl.value,
                content: content,
                author: authorEl.value.trim() || null
            })
        });

        if (response.ok) {
            contentEl.value = '';
            loadAnnotations(entityType, entityId);
        }
    } catch (error) {
        // Silent fail
    }
}

/**
 * Delete an annotation
 */
async function deleteAnnotation(annotationId, entityType, entityId) {
    try {
        const response = await fetch(`/api/annotations/${annotationId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadAnnotations(entityType, entityId);
        }
    } catch (error) {
        // Silent fail
    }
}
