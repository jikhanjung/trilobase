# Getting Started

Trilobase can be used in three ways: as a standalone executable, from Python source, or as an MCP server for LLM integration.

---

## Option 1: Standalone Executable (Recommended)

The simplest way to use Trilobase. No Python installation required.

1. Download `trilobase.exe` (Windows) or `trilobase` (Linux) from the [Releases page](https://github.com/jikhanjung/trilobase/releases)
2. Run the executable
3. Click **"▶ Start Server"** in the GUI control panel
4. Your browser opens automatically at `http://localhost:8080`

All data and the web server are bundled in a single file. User annotations are stored separately in `trilobase_overlay.db` and persist across updates.

---

## Option 2: Python Development Mode

For developers or users who need to modify the source code.

### Requirements

- Python 3.8+
- [scoda-engine](https://github.com/jikhanjung/scoda-engine) (runtime)

### Installation

```bash
git clone https://github.com/jikhanjung/trilobase.git
cd trilobase
pip install -e /path/to/scoda-engine[dev]
```

### Run Web Server

```bash
python -m scoda_engine.serve trilobase.scoda
```

Open `http://localhost:8080` in your browser.

### Run Tests

```bash
pytest tests/
```

---

## Option 3: MCP Server (LLM Integration)

Trilobase includes a **Model Context Protocol (MCP)** server that lets Claude or other LLMs query the trilobite database using natural language.

### Method A: Using the executable (recommended)

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "C:\\path\\to\\trilobase_mcp.exe"
    }
  }
}
```

### Method B: Using Python source

```bash
pip install mcp starlette uvicorn
```

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "python",
      "args": ["/absolute/path/to/trilobase/mcp_server.py"],
      "cwd": "/absolute/path/to/trilobase"
    }
  }
}
```

Restart Claude Desktop after updating the config.

### Example Queries

Once connected, you can ask Claude:

- "Show trilobite genera found in China"
- "What are the synonyms of Paradoxides?"
- "List genera in Family Paradoxididae"
- "What are the data sources for this database?"
- "Add a note to Agnostus: 'Check formation data'"

---

## Direct SQL Access

You can also query the database directly with SQLite:

```bash
sqlite3 db/trilobase.db "SELECT name, author, year FROM taxonomic_ranks WHERE rank='Genus' AND is_valid=1 LIMIT 10;"
```

For cross-database queries (geographic/stratigraphic data), attach PaleoCore:

```sql
ATTACH DATABASE 'db/paleocore.db' AS pc;

SELECT g.name, c.name AS country
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN pc.countries c ON gl.country_id = c.id
WHERE g.name = 'Paradoxides';
```
