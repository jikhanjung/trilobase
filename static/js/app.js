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
document.addEventListener('DOMContentLoaded', async () => {
    genusModal = new bootstrap.Modal(document.getElementById('genusModal'));
    await loadManifest();

    // Determine initial view from manifest (default to taxonomy_tree for legacy)
    if (manifest && manifest.views) {
        const viewKeys = Object.keys(manifest.views).filter(k => manifest.views[k].type !== 'detail');
        if (manifest.default_view && manifest.views[manifest.default_view]) {
            currentView = manifest.default_view;
        } else if (viewKeys.length > 0 && !manifest.views['taxonomy_tree']) {
            currentView = viewKeys[0];
        }
        // Rebuild tabs with correct currentView
        buildViewTabs();
        switchToView(currentView);
    } else {
        // Legacy fallback: no manifest, just load tree
        loadTree();
    }
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

        // Show package name in navbar
        if (data.package && data.package.name) {
            const el = document.getElementById('navbar-pkg-name');
            if (el) el.textContent = `${data.package.name} v${data.package.version}`;
        }
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
    const chartContainer = document.getElementById('view-chart');

    treeContainer.style.display = 'none';
    tableContainer.style.display = 'none';
    chartContainer.style.display = 'none';

    if (view.type === 'tree') {
        treeContainer.style.display = '';
        loadTree();
    } else if (view.type === 'table') {
        tableContainer.style.display = '';
        tableViewSort = view.default_sort || null;
        tableViewSearchTerm = '';
        renderTableView(viewKey);
    } else if (view.type === 'chart') {
        chartContainer.style.display = '';
        renderChronostratChart(viewKey);
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
        const queryUrl = `/api/queries/${view.source_query}/execute`;
        const response = await fetch(queryUrl);
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

    // Manifest-driven click handler
    const rowClick = view.on_row_click;
    const getClick = rowClick
        ? (row) => `onclick="openDetail('${rowClick.detail_view}', ${row[rowClick.id_key]})"`
        : null;

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
 * Render ICS Chronostratigraphic Chart as a hierarchical colored table
 */
async function renderChronostratChart(viewKey) {
    const view = manifest.views[viewKey];
    if (!view) return;

    const opts = view.chart_options || {};

    const header = document.getElementById('chart-view-header');
    const body = document.getElementById('chart-view-body');

    header.innerHTML = `<h5><i class="bi ${view.icon || 'bi-clock-history'}"></i> ${view.title}</h5>
                        <p class="text-muted mb-0">${view.description || ''}</p>`;

    body.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const queryUrl = `/api/queries/${view.source_query}/execute`;
        const response = await fetch(queryUrl);
        if (!response.ok) {
            body.innerHTML = '<div class="text-danger">Error loading data</div>';
            return;
        }
        const data = await response.json();
        const rows = data.rows;

        // Build rank→column mapping from manifest
        const rankColumns = opts.rank_columns || [
            {rank: 'Eon'}, {rank: 'Era'}, {rank: 'Period'},
            {rank: 'Sub-Period'}, {rank: 'Epoch'}, {rank: 'Age'}
        ];
        const rankColMap = {};
        rankColumns.forEach((rc, i) => { rankColMap[rc.rank] = i; });
        const colCount = rankColumns.length + 1; // +1 for value column

        // Build tree from flat data
        const tree = buildChartTree(rows, opts);
        // Compute leaf counts for rowspan
        tree.forEach(node => computeLeafCount(node));
        // Collect leaf rows (each row = root→leaf path)
        const leafRows = [];
        tree.forEach(node => collectLeafRows(node, [], leafRows, 0, rankColMap, opts));

        // Render HTML table
        body.innerHTML = renderChartHTML(leafRows, opts);
    } catch (error) {
        body.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
    }
}

/**
 * Build tree structure from flat ICS data (manifest-driven).
 * Nodes with ranks in skip_ranks are skipped; their children are promoted to root level.
 */
function buildChartTree(rows, opts) {
    opts = opts || {};
    const idKey = opts.id_key || 'id';
    const parentKey = opts.parent_key || 'parent_id';
    const rankKey = opts.rank_key || 'rank';
    const orderKey = opts.order_key || 'display_order';
    const skipRanks = opts.skip_ranks || ['Super-Eon'];

    const byId = {};
    rows.forEach(r => { byId[r[idKey]] = { ...r, children: [] }; });

    const roots = [];
    rows.forEach(r => {
        const node = byId[r[idKey]];
        if (r[parentKey] && byId[r[parentKey]]) {
            const parent = byId[r[parentKey]];
            // Skip specified ranks: promote their children to root
            if (skipRanks.includes(parent[rankKey])) {
                roots.push(node);
            } else {
                parent.children.push(node);
            }
        } else if (!r[parentKey]) {
            // No parent — could be a skipped rank or actual root
            if (skipRanks.includes(r[rankKey])) {
                // Don't add skipped rank itself; its children will be promoted
            } else {
                roots.push(node);
            }
        }
    });

    // Sort children by order_key ascending
    function sortChildren(node) {
        node.children.sort((a, b) => (a[orderKey] || 0) - (b[orderKey] || 0));
        node.children.forEach(sortChildren);
    }
    roots.sort((a, b) => (a[orderKey] || 0) - (b[orderKey] || 0));
    roots.forEach(sortChildren);

    return roots;
}

/**
 * Compute leaf count for each node (= rowspan).
 * A leaf node (no children) has leafCount = 1.
 */
function computeLeafCount(node) {
    if (node.children.length === 0) {
        node.leafCount = 1;
        return 1;
    }
    let count = 0;
    node.children.forEach(c => { count += computeLeafCount(c); });
    node.leafCount = count;
    return count;
}

/**
 * Check if a node has a direct child at the next rank column (for colspan calculation).
 * e.g., Period (col 2) checking if any child is Sub-Period (col 3).
 */
function hasDirectChildRank(node, parentCol, rankColMap, rankKey) {
    return node.children.some(c => rankColMap[c[rankKey]] === parentCol + 1);
}

/**
 * Collect leaf rows via DFS. Each leaf produces one table row.
 * path = array of { node, col, colspan, rowspan } for ancestors that start at this leaf's row.
 * parentEndCol = the first column after the parent's span (used to detect gaps like Pridoli)
 * rankColMap = rank→column index mapping from chart_options
 */
function collectLeafRows(node, ancestorPath, leafRows, parentEndCol, rankColMap, opts) {
    opts = opts || {};
    const rankKey = opts.rank_key || 'rank';
    const maxCol = Object.keys(rankColMap).length - 1; // last rank column index

    let col = rankColMap[node[rankKey]] !== undefined ? rankColMap[node[rankKey]] : maxCol;

    // If node has children but no direct child at col+1, extend colspan to bridge the gap
    let colspan = 1;
    if (node.children.length > 0 && !hasDirectChildRank(node, col, rankColMap, rankKey)) {
        const childCols = node.children.map(c => rankColMap[c[rankKey]]).filter(c => c !== undefined);
        if (childCols.length > 0) {
            const minChildCol = Math.min(...childCols);
            if (minChildCol > col + 1) {
                colspan = minChildCol - col;
            }
        }
    }

    // Adjust for parent-child column gap (e.g., Pridoli: Age directly under Period)
    if (parentEndCol !== undefined && col > parentEndCol) {
        const originalEndCol = col + colspan - 1;
        col = parentEndCol;
        colspan = originalEndCol - col + 1;
    }

    const entry = { node, col, colspan, rowspan: node.leafCount };
    const myEndCol = col + colspan;

    if (node.children.length === 0) {
        // Leaf: extend colspan to fill remaining columns up to last rank column
        const endCol = col + colspan - 1;
        if (endCol < maxCol) {
            colspan = maxCol - col + 1; // extend to last rank col inclusive
            entry.colspan = colspan;
        }

        // Build the row: ancestor cells + this cell
        const row = [...ancestorPath, entry];
        leafRows.push(row);
    } else {
        // Non-leaf: first child inherits this node in its path, rest don't
        node.children.forEach((child, i) => {
            if (i === 0) {
                collectLeafRows(child, [...ancestorPath, entry], leafRows, myEndCol, rankColMap, opts);
            } else {
                collectLeafRows(child, [], leafRows, myEndCol, rankColMap, opts);
            }
        });
    }
}

/**
 * Determine if a hex color is light (for text contrast)
 */
function isLightColor(hex) {
    if (!hex) return true;
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    // Luminance formula
    const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return lum > 0.5;
}

/**
 * Render the ICS chart as an HTML table (manifest-driven)
 */
function renderChartHTML(leafRows, opts) {
    opts = opts || {};
    const rankColumns = opts.rank_columns || [
        {rank: 'Eon', label: 'Eon'}, {rank: 'Era', label: 'Era'},
        {rank: 'Period', label: 'System / Period'}, {rank: 'Sub-Period', label: 'Sub-Period'},
        {rank: 'Epoch', label: 'Series / Epoch'}, {rank: 'Age', label: 'Stage / Age'}
    ];
    const valueCol = opts.value_column || {key: 'start_mya', label: 'Age (Ma)'};
    const cellClick = opts.cell_click || {detail_view: 'chronostrat_detail', id_key: 'id'};
    const labelKey = opts.label_key || 'name';
    const colorKey = opts.color_key || 'color';
    const idKey = opts.id_key || 'id';

    const headers = rankColumns.map(rc => rc.label).concat(valueCol.label);

    let html = '<table class="ics-chart"><thead><tr>';
    headers.forEach(h => { html += `<th>${h}</th>`; });
    html += '</tr></thead><tbody>';

    leafRows.forEach(row => {
        html += '<tr>';
        // Render ancestor + leaf cells
        row.forEach(entry => {
            const n = entry.node;
            const bgColor = n[colorKey] || '#f8f9fa';
            const textColor = isLightColor(bgColor) ? '#222' : '#fff';
            const rs = entry.rowspan > 1 ? ` rowspan="${entry.rowspan}"` : '';
            const cs = entry.colspan > 1 ? ` colspan="${entry.colspan}"` : '';
            const vk = valueCol.key;
            const title = n[vk] != null ? `${n[labelKey]} (${n[vk]}–${n.end_mya || 0} Ma)` : n[labelKey];
            html += `<td${rs}${cs} style="background-color:${bgColor}; color:${textColor};" `
                  + `title="${title}" onclick="openDetail('${cellClick.detail_view}', ${n[cellClick.id_key || idKey]})">`
                  + `${n[labelKey]}</td>`;
        });

        // Value column: use the leaf node's value
        const leaf = row[row.length - 1].node;
        const ageMa = leaf[valueCol.key] != null ? leaf[valueCol.key] : '';
        html += `<td class="ics-age">${ageMa}</td>`;

        html += '</tr>';
    });

    html += '</tbody></table>';
    return html;
}

/**
 * Build nested tree from flat rows using parent_key.
 */
function buildTreeFromFlat(rows, opts) {
    const idKey = opts.id_key || 'id';
    const parentKey = opts.parent_key || 'parent_id';

    const byId = {};
    rows.forEach(r => { byId[r[idKey]] = { ...r, children: [] }; });

    const roots = [];
    rows.forEach(r => {
        const node = byId[r[idKey]];
        const pid = r[parentKey];
        if (pid && byId[pid]) {
            byId[pid].children.push(node);
        } else if (!pid) {
            roots.push(node);
        }
    });

    // Sort children alphabetically by label
    const labelKey = opts.label_key || 'name';
    function sortChildren(node) {
        node.children.sort((a, b) => (a[labelKey] || '').localeCompare(b[labelKey] || ''));
        node.children.forEach(sortChildren);
    }
    roots.sort((a, b) => (a[labelKey] || '').localeCompare(b[labelKey] || ''));
    roots.forEach(sortChildren);

    return roots;
}

/**
 * Load taxonomy tree from manifest source_query (flat data → client-side tree)
 */
async function loadTree() {
    const container = document.getElementById('tree-container');

    try {
        // Use manifest source_query if available, otherwise fallback
        let tree;
        const viewDef = manifest && manifest.views && manifest.views['taxonomy_tree'];
        if (viewDef && viewDef.source_query && viewDef.tree_options) {
            const queryUrl = `/api/queries/${viewDef.source_query}/execute`;
            const response = await fetch(queryUrl);
            if (!response.ok) throw new Error('Failed to load tree data');
            const data = await response.json();
            tree = buildTreeFromFlat(data.rows, viewDef.tree_options);
        } else {
            const response = await fetch('/api/tree');
            tree = await response.json();
        }
        container.innerHTML = '';

        tree.forEach(node => {
            container.appendChild(createTreeNode(node));
        });
    } catch (error) {
        container.innerHTML = `<div class="text-danger">Error loading tree: ${error.message}</div>`;
    }
}

/**
 * Create tree node element recursively (manifest-driven)
 */
function createTreeNode(node) {
    const div = document.createElement('div');
    div.className = 'tree-node';

    const opts = (manifest && manifest.views && manifest.views['taxonomy_tree'] &&
                  manifest.views['taxonomy_tree'].tree_options) || {};
    const leafRank = opts.leaf_rank || 'Family';
    const rankKey = opts.rank_key || 'rank';
    const labelKey = opts.label_key || 'name';
    const countKey = opts.count_key || 'genera_count';
    const idKey = opts.id_key || 'id';

    const hasChildren = node.children && node.children.length > 0;
    const isLeaf = node[rankKey] === leafRank;

    // Node content
    const content = document.createElement('div');
    content.className = `tree-node-content rank-${node[rankKey]}`;
    content.dataset.id = node[idKey];
    content.dataset.rank = node[rankKey];
    content.dataset.name = node[labelKey];

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
    if (isLeaf) {
        icon.innerHTML = '<i class="bi bi-folder-fill"></i>';
    } else {
        icon.innerHTML = '<i class="bi bi-folder2"></i>';
    }
    content.appendChild(icon);

    // Label
    const label = document.createElement('span');
    label.className = 'tree-label';
    label.textContent = node[labelKey];
    content.appendChild(label);

    // Count (for leaf nodes)
    if (isLeaf && node[countKey] > 0) {
        const count = document.createElement('span');
        count.className = 'tree-count';
        count.textContent = `(${node[countKey]})`;
        content.appendChild(count);
    }

    // Info icon — detail view from manifest
    const infoBtn = document.createElement('span');
    infoBtn.className = 'tree-info';
    infoBtn.innerHTML = '<i class="bi bi-info-circle"></i>';
    infoBtn.title = 'View details';
    infoBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const infoOpts = opts.on_node_info || {};
        openDetail(infoOpts.detail_view || 'rank_detail', node[infoOpts.id_key || idKey]);
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

        if (isLeaf) {
            selectTreeLeaf(node[idKey], node[labelKey]);
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
 * Select a tree leaf node and load its items (manifest-driven)
 */
async function selectTreeLeaf(leafId, leafName) {
    // Update selection highlight
    document.querySelectorAll('.tree-node-content.selected').forEach(el => {
        el.classList.remove('selected');
    });
    document.querySelector(`.tree-node-content[data-id="${leafId}"]`)?.classList.add('selected');

    selectedFamilyId = leafId;

    const opts = (manifest && manifest.views && manifest.views['taxonomy_tree'] &&
                  manifest.views['taxonomy_tree'].tree_options) || {};
    const filterDef = opts.item_valid_filter || {};

    // Update header with filter checkbox
    const header = document.getElementById('list-header');
    header.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="bi bi-folder-fill"></i> ${leafName}</h5>
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="validOnlyCheck"
                       ${showOnlyValid ? 'checked' : ''} onchange="toggleValidFilter()">
                <label class="form-check-label" for="validOnlyCheck">${filterDef.label || 'Valid only'}</label>
            </div>
        </div>`;

    // Load items via named query from manifest
    const container = document.getElementById('list-container');
    container.innerHTML = '<div class="loading">Loading genera...</div>';

    try {
        let items;
        if (opts.item_query && opts.item_param) {
            const baseUrl = `/api/queries/${opts.item_query}/execute`;
            const url = `${baseUrl}?${opts.item_param}=${leafId}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load items');
            const data = await response.json();
            items = data.rows;
        } else {
            // Fallback to legacy API
            const response = await fetch(`/api/family/${leafId}/genera`);
            const data = await response.json();
            items = data.genera;
        }

        currentGenera = items;  // Store for filtering
        renderTreeItemTable();

    } catch (error) {
        container.innerHTML = `<div class="text-danger">Error loading genera: ${error.message}</div>`;
    }
}

/** Legacy alias for backward compatibility (used by navigateToRank, navigateToGenus) */
function selectFamily(familyId, familyName) {
    selectTreeLeaf(familyId, familyName);
}

/**
 * Toggle valid-only filter
 */
function toggleValidFilter() {
    showOnlyValid = document.getElementById('validOnlyCheck').checked;
    renderTreeItemTable();
}

/**
 * Render tree leaf item table with current filter (manifest-driven columns)
 */
function renderTreeItemTable() {
    const container = document.getElementById('list-container');

    const opts = (manifest && manifest.views && manifest.views['taxonomy_tree'] &&
                  manifest.views['taxonomy_tree'].tree_options) || {};
    const filterDef = opts.item_valid_filter || {};
    const filterKey = filterDef.key || 'is_valid';
    const columns = opts.item_columns || [
        {key: 'name', label: 'Genus', italic: true},
        {key: 'author', label: 'Author'},
        {key: 'year', label: 'Year'},
        {key: 'type_species', label: 'Type Species', truncate: 40},
        {key: 'location', label: 'Location', truncate: 30}
    ];
    const clickDef = opts.on_item_click || {detail_view: 'genus_detail', id_key: 'id'};
    const idKey = opts.id_key || 'id';

    const genera = showOnlyValid
        ? currentGenera.filter(g => g[filterKey])
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
    const validCount = currentGenera.filter(g => g[filterKey]).length;
    const invalidCount = currentGenera.length - validCount;
    const statsText = showOnlyValid
        ? `Showing ${validCount} valid genera` + (invalidCount > 0 ? ` (${invalidCount} invalid hidden)` : '')
        : `Showing all ${currentGenera.length} genera (${validCount} valid, ${invalidCount} invalid)`;

    let html = `<div class="genera-stats text-muted mb-2">${statsText}</div>`;
    html += '<table class="genus-table"><thead><tr>';
    columns.forEach(col => { html += `<th>${col.label}</th>`; });
    html += '</tr></thead><tbody>';

    genera.forEach(g => {
        const rowClass = g[filterKey] ? '' : 'invalid';
        html += `<tr class="${rowClass}" onclick="openDetail('${clickDef.detail_view}', ${g[clickDef.id_key || idKey]})">`;
        columns.forEach(col => {
            let val = g[col.key];
            if (col.truncate && val) val = truncate(val, col.truncate);
            if (val == null) val = '';
            if (col.italic) {
                html += `<td class="genus-name"><i>${val}</i></td>`;
            } else {
                html += `<td>${val}</td>`;
            }
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
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
    openDetail('rank_detail', rankId);
}

/**
 * Navigate to a Genus from children list
 */
function navigateToGenus(genusId, familyId, familyName) {
    expandTreeToNode(familyId);
    selectFamily(familyId, familyName);
    openDetail('genus_detail', genusId);
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
            `<a class="detail-link" onclick="openDetail('chronostrat_detail', ${m.id})">${m.name}</a>` +
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
            `<a class="detail-link" onclick="openDetail('rank_detail', ${h.id})">${h.name}</a>` +
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
        const annUrl = `/api/annotations/${entityType}/${entityId}`;
        const response = await fetch(annUrl);
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
        const postUrl = '/api/annotations';
        const response = await fetch(postUrl, {
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
        const delUrl = `/api/annotations/${annotationId}`;
        const response = await fetch(delUrl, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadAnnotations(entityType, entityId);
        }
    } catch (error) {
        // Silent fail
    }
}


// ═══════════════════════════════════════════════════════════════════════
// Generic Manifest-Driven Detail Renderer (Phase 39)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Open a detail view by manifest key. Dispatches to renderDetailFromManifest.
 */
async function openDetail(viewKey, entityId) {
    if (!manifest || !manifest.views[viewKey]) return;
    await renderDetailFromManifest(viewKey, entityId);
}

/**
 * Resolve a dotted path (e.g., "parent.name") on a data object.
 */
function resolveDataPath(data, path) {
    if (!data || !path) return undefined;
    return path.split('.').reduce((obj, key) => (obj != null ? obj[key] : undefined), data);
}

/**
 * Check a condition against data. Supports:
 *  - string key: truthy check (arrays check length > 0)
 *  - falsy/missing condition: always true
 */
function checkCondition(data, condition) {
    if (!condition) return true;
    const val = resolveDataPath(data, condition);
    if (Array.isArray(val)) return val.length > 0;
    return !!val;
}

/**
 * Build the modal title from a title_template and data.
 */
function buildDetailTitle(template, data) {
    if (!template || !template.format) return data.name || '';
    let title = template.format;
    // Replace {icon} with Bootstrap icon
    if (template.icon) {
        title = title.replace('{icon}', `<i class="bi ${template.icon}"></i>`);
    } else {
        title = title.replace('{icon}', '');
    }
    // Replace {field} placeholders
    title = title.replace(/\{(\w+)\}/g, (match, key) => {
        const val = data[key];
        return (val != null && val !== '') ? val : '';
    });
    return title.trim();
}

/**
 * Compute a derived value. Built-in compute functions.
 */
function computeValue(computeName, data, row) {
    const src = row || data;
    switch (computeName) {
        case 'time_range':
            if (src.start_mya != null && src.end_mya != null)
                return `${src.start_mya} — ${src.end_mya} Ma`;
            return '-';
        default:
            return '-';
    }
}

/**
 * Format a cell value according to field definition.
 */
function formatFieldValue(field, value, data) {
    const fmt = field.format;

    if (fmt === 'computed') {
        value = computeValue(field.compute, data);
    }

    if (value == null || value === '') {
        // For boolean, treat null/undefined as false
        if (fmt === 'boolean') return field.false_label || 'No';
        return '-';
    }

    switch (fmt) {
        case 'italic':
            return `<i>${value}</i>`;
        case 'boolean': {
            const cls = value ? '' : (field.false_class || '');
            const label = value ? (field.true_label || 'Yes') : (field.false_label || 'No');
            return cls ? `<span class="${cls}">${label}</span>` : label;
        }
        case 'link': {
            const linkDef = field.link;
            if (!linkDef) return value;
            const linkId = resolveDataPath(data, linkDef.id_path || linkDef.id_key);
            if (linkId == null) return value;
            return `<a class="detail-link" onclick="openDetail('${linkDef.detail_view}', ${linkId})">${value}</a>`;
        }
        case 'color_chip':
            return `<span class="color-chip" style="background-color:${value}"></span> ${value}`;
        case 'code':
            return `<code>${value}</code>`;
        case 'hierarchy':
            return buildHierarchyHTML(data);
        case 'temporal_range':
            return buildTemporalRangeHTML(data);
        case 'computed':
            return value; // already computed above
        default:
            return value;
    }
}

/**
 * Render a field_grid section.
 */
function renderFieldGrid(section, data) {
    const fields = section.fields || [];
    let gridHtml = '';

    for (const field of fields) {
        // Per-field condition check
        if (field.condition && !checkCondition(data, field.condition)) continue;

        let value = resolveDataPath(data, field.key);
        let formatted = formatFieldValue(field, value, data);

        // Suffix support (e.g., year + year_suffix)
        if (field.suffix_key) {
            const suffix = resolveDataPath(data, field.suffix_key);
            if (suffix) {
                if (field.suffix_format) {
                    formatted += ` <small class="text-muted">${field.suffix_format.replace('{value}', suffix)}</small>`;
                } else {
                    formatted += suffix;
                }
            }
        }

        gridHtml += `
            <span class="detail-label">${field.label}:</span>
            <span class="detail-value">${formatted}</span>`;
    }

    if (!gridHtml) return '';
    return `
        <div class="detail-section">
            <h6>${section.title}</h6>
            <div class="detail-grid">${gridHtml}
            </div>
        </div>`;
}

/**
 * Render a linked_table section.
 */
function renderLinkedTable(section, data) {
    const rows = data[section.data_key] || [];
    const columns = section.columns || [];
    const onClick = section.on_row_click;
    const title = section.title.replace('{count}', rows.length);

    // Empty handling
    if (rows.length === 0) {
        if (section.show_empty) {
            return `
                <div class="detail-section">
                    <h6>${title}</h6>
                    <p class="text-muted">${section.empty_message || 'No data.'}</p>
                </div>`;
        }
        return '';
    }

    // Header
    let html = `
        <div class="detail-section">
            <h6>${title}</h6>
            <div class="genera-list">
                <table class="manifest-table">
                    <thead><tr>`;
    columns.forEach(col => {
        html += `<th>${col.label}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Rows
    rows.forEach(row => {
        const clickAttr = onClick
            ? ` onclick="openDetail('${onClick.detail_view}', ${row[onClick.id_key]})"`
            : '';
        html += `<tr${clickAttr}>`;

        columns.forEach(col => {
            let val = (col.format === 'computed')
                ? computeValue(col.compute, data, row)
                : row[col.key];

            // Column-level link (e.g., region link within genera table)
            if (col.link && val) {
                const linkId = row[col.link.id_key];
                if (linkId != null) {
                    val = `<a class="detail-link" onclick="event.stopPropagation(); openDetail('${col.link.detail_view}', ${linkId})">${val}</a>`;
                }
            } else if (col.format === 'boolean') {
                val = val ? 'Yes' : 'No';
            } else if (col.format === 'color_chip') {
                val = val ? `<span class="color-chip" style="background-color:${val}"></span> ${val}` : '';
            } else if (col.format === 'code') {
                val = val ? `<code>${val}</code>` : '';
            } else if (col.italic) {
                val = val ? `<i>${val}</i>` : '';
            } else {
                val = val != null ? val : '';
            }

            html += `<td>${val}</td>`;
        });

        html += '</tr>';
    });

    html += '</tbody></table></div></div>';
    return html;
}

/**
 * Render a tagged_list section (badge + text items).
 */
function renderTaggedList(section, data) {
    const items = data[section.data_key] || [];
    if (items.length === 0) return '';

    let html = `
        <div class="detail-section">
            <h6>${section.title}</h6>
            <ul class="list-unstyled">`;

    items.forEach(item => {
        const badge = item[section.badge_key] || '';
        const text = item[section.text_key] || '';
        const badgeHtml = section.badge_format === 'code'
            ? `<code>${badge}</code>`
            : `<span class="badge bg-secondary">${badge}</span>`;
        html += `<li>${badgeHtml} <small class="text-muted ms-1">(${text})</small></li>`;
    });

    html += '</ul></div>';
    return html;
}

/**
 * Render a raw_text section (monospace or paragraph).
 */
function renderRawText(section, data) {
    const value = data[section.data_key];
    if (!value) return '';

    const inner = section.format === 'paragraph'
        ? `<p>${value}</p>`
        : `<div class="raw-entry">${value}</div>`;

    return `
        <div class="detail-section">
            <h6>${section.title}</h6>
            ${inner}
        </div>`;
}

/**
 * Render an annotations section (My Notes with CRUD).
 */
function renderAnnotationsSection(section, data) {
    let entityType;
    if (section.entity_type) {
        entityType = section.entity_type;
    } else if (section.entity_type_from) {
        entityType = (data[section.entity_type_from] || '').toLowerCase();
    }
    if (!entityType) return '';
    return buildAnnotationSectionHTML(entityType, data.id);
}

/**
 * Built-in renderer: genus geography section.
 * Handles locations/formations with country/region links, fallback to raw text.
 */
function renderGenusGeography(data) {
    let geoGridHtml = '';

    if (data.locations && data.locations.length > 0) {
        const locLinks = data.locations.map(l => {
            let link = `<a class="detail-link" onclick="openDetail('country_detail', ${l.country_id})">${l.country_name}</a>`;
            if (l.region_id && l.region_name) {
                link += ` &gt; <a class="detail-link" onclick="openDetail('region_detail', ${l.region_id})">${l.region_name}</a>`;
            }
            return link;
        }).join(', ');
        geoGridHtml += `
            <span class="detail-label">Country:</span>
            <span class="detail-value">${locLinks}</span>`;
    } else if (data.location) {
        geoGridHtml += `
            <span class="detail-label">Location:</span>
            <span class="detail-value">${data.location}</span>`;
    }

    if (data.formations && data.formations.length > 0) {
        const fmtLinks = data.formations.map(f =>
            `<a class="detail-link" onclick="openDetail('formation_detail', ${f.id})">${f.name}</a>${f.period ? ' (' + f.period + ')' : ''}`
        ).join(', ');
        geoGridHtml += `
            <span class="detail-label">Formation:</span>
            <span class="detail-value">${fmtLinks}</span>`;
    } else if (data.formation) {
        geoGridHtml += `
            <span class="detail-label">Formation:</span>
            <span class="detail-value">${data.formation}</span>`;
    }

    if (!geoGridHtml) return '';
    return `
        <div class="detail-section">
            <h6>Geographic Information</h6>
            <div class="detail-grid">${geoGridHtml}
            </div>
        </div>`;
}

/**
 * Built-in renderer: synonym list section.
 */
function renderSynonymList(section, data) {
    const synonyms = data[section.data_key] || [];
    if (synonyms.length === 0) return '';

    let html = `
        <div class="detail-section">
            <h6>Synonymy</h6>
            <ul class="list-unstyled">`;

    synonyms.forEach(s => {
        const seniorLink = s.senior_taxon_id
            ? `<a href="#" class="synonym-link" onclick="openDetail('genus_detail', ${s.senior_taxon_id}); return false;"><i>${s.senior_name}</i></a>`
            : `<i>${s.senior_name}</i>`;
        html += `
            <li>
                <span class="badge bg-secondary badge-synonym">${s.synonym_type}</span>
                ${seniorLink}
                ${s.fide_author ? `<small class="text-muted">fide ${s.fide_author}${s.fide_year ? ', ' + s.fide_year : ''}</small>` : ''}
            </li>`;
    });

    html += '</ul></div>';
    return html;
}

/**
 * Built-in renderer: rank statistics section.
 */
function renderRankStatistics(data) {
    if (!data.genera_count && (!data.children_counts || data.children_counts.length === 0)) return '';

    let html = `
        <div class="detail-section">
            <h6>Statistics</h6>
            <div class="detail-grid">`;

    if (data.genera_count) {
        html += `
            <span class="detail-label">Genera:</span>
            <span class="detail-value">${data.genera_count}</span>`;
    }

    if (data.children_counts) {
        data.children_counts.forEach(c => {
            if (c.rank === 'Genus' && data.genera_count) return;
            html += `
                <span class="detail-label">${c.rank}:</span>
                <span class="detail-value">${c.count}</span>`;
        });
    }

    html += '</div></div>';
    return html;
}

/**
 * Built-in renderer: rank children list section.
 */
function renderRankChildren(section, data) {
    const children = data[section.data_key] || [];
    if (children.length === 0) return '';

    const title = `Children (${children.length}${children.length >= 20 ? '+' : ''})`;
    let html = `
        <div class="detail-section">
            <h6>${title}</h6>
            <ul class="list-unstyled children-list">`;

    children.forEach(c => {
        if (c.rank === 'Genus') {
            html += `
            <li class="clickable" onclick="navigateToGenus(${c.id}, ${data.id}, '${data.name.replace(/'/g, "\\'")}')">
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
    return html;
}

/**
 * Dispatch section rendering by type.
 */
function renderDetailSection(section, data) {
    // Section-level condition check
    if (section.condition && !checkCondition(data, section.condition)) return '';

    switch (section.type) {
        case 'field_grid':      return renderFieldGrid(section, data);
        case 'linked_table':    return renderLinkedTable(section, data);
        case 'tagged_list':     return renderTaggedList(section, data);
        case 'raw_text':        return renderRawText(section, data);
        case 'annotations':     return renderAnnotationsSection(section, data);
        case 'genus_geography': return renderGenusGeography(data);
        case 'synonym_list':    return renderSynonymList(section, data);
        case 'rank_statistics': return renderRankStatistics(data);
        case 'rank_children':   return renderRankChildren(section, data);
        default:                return '';
    }
}

/**
 * Main entry point: render a detail view from manifest definition.
 */
async function renderDetailFromManifest(viewKey, entityId) {
    const view = manifest.views[viewKey];
    if (!view || view.type !== 'detail') return;

    const modalBody = document.getElementById('genusModalBody');
    const modalTitle = document.getElementById('genusModalTitle');

    modalBody.innerHTML = '<div class="loading">Loading...</div>';
    genusModal.show();

    try {
        const url = view.source.replace('{id}', entityId);
        const response = await fetch(url);
        const data = await response.json();

        // Title
        modalTitle.innerHTML = buildDetailTitle(view.title_template, data);

        // Sections
        let html = '';
        for (const section of view.sections) {
            html += renderDetailSection(section, data);
        }
        modalBody.innerHTML = html;

        // Post-render: load annotations for any annotations sections
        for (const section of view.sections) {
            if (section.type === 'annotations') {
                let entityType;
                if (section.entity_type) {
                    entityType = section.entity_type;
                } else if (section.entity_type_from) {
                    entityType = (data[section.entity_type_from] || '').toLowerCase();
                }
                if (entityType) {
                    loadAnnotations(entityType, data.id);
                }
            }
        }

    } catch (error) {
        modalBody.innerHTML = `<div class="text-danger">Error loading details: ${error.message}</div>`;
    }
}
