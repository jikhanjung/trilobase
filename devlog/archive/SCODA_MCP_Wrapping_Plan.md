# SCODA MCP Wrapping Plan
*Model Context Protocol integration for a local, stateful knowledge system*

---

## 1. Purpose

This document outlines a technical and conceptual plan for wrapping the existing **SPA + API–based local web system** of SCODA as a **Model Context Protocol (MCP)** server.

The goals of this integration are to:

- Preserve the current SCODA architecture with minimal changes
- Allow both human users (via SPA UI) and language models (via MCP) to access the **same deterministic query layer**
- Constrain LLMs to the role of **evidence-grounded narration**, not judgment or definition

---

## 2. Current SCODA Architecture (As-Is)

```
[SPA UI]
   ↓ REST/JSON
[Local Web Server]
   ├─ Domain Logic
   ├─ DB Query Layer
   └─ Local Database (SCODA / Trilobase)
```

Key characteristics:
- Fully local execution on the user’s machine
- API-driven architecture
- Explicit modeling of concepts, references, and historical usages
- Snapshots (PDF, image, web views) are derived from database states

---

## 3. Conceptual Position of MCP Integration (To-Be)

MCP does not introduce a new server tier, but **promotes the existing local server** to an LLM-facing interface.

```
                  ┌─ SPA (Human)
[Local API Server]┤
                  └─ MCP Server (LLM)
```

- Single source of truth (DB + query logic)
- Different access modalities:
  - SPA → REST API
  - LLM → MCP tools

---

## 4. Responsibilities of the MCP Server

Within SCODA, the MCP server is responsible for:

1. **Tool Registry**
   - Exposing a predefined set of domain-specific query tools
2. **Execution Control**
   - LLMs may select tools, but execution is performed by the server
3. **Evidence Pack Construction**
   - Transforming DB results into structured, bounded inputs for LLMs
4. **Context Boundary Enforcement**
   - Preventing use of information outside the supplied evidence

---

## 5. API-to-MCP Tool Mapping Strategy

### 5.1 Design Principles

- Reuse existing REST API endpoints
- MCP tools act as conceptual wrappers
- No direct exposure of SQL or DB schema

### 5.2 Example Mapping

| REST API Endpoint | MCP Tool |
|------------------|----------|
| GET /api/concepts/{id} | get_concept |
| GET /api/concepts/{id}/usages | get_concept_usages |
| GET /api/concepts/{id}/relations | get_related_concepts |
| GET /api/concepts/{id}/state?year=Y | get_concept_state_at_year |

All MCP tools are:
- Read-only
- Deterministic
- Explicitly scoped

---

## 6. Evidence Pack Design

LLMs never receive raw DB output. Instead, SCODA constructs **Evidence Packs**.

### 6.1 Example Structure

```json
{
  "concept": { "id": "...", "label": "...", "status": "official|historical" },
  "timeline": [
    { "year": 1934, "author": "...", "usage": "...", "ref_id": "..." }
  ],
  "relations": [
    { "type": "replaced_by", "target": "..." }
  ],
  "mappings": [
    { "target": "ICS_unit", "confidence": "approximate" }
  ],
  "references": [ "Ref1934", "Ref1952" ]
}
```

### 6.2 Design Constraints

- Evidence must be sufficient but minimal
- Every claim must link to a reference ID
- Uncertainty is explicitly encoded at the data level

---

## 7. Prompt Branching Strategy (Critical)

Prompt selection is **data-driven**, not model-driven.

### 7.1 Required Metadata Fields

```json
{
  "authority": "ICS | regional | author-specific",
  "current_validity": "ratified | unratified | obsolete"
}
```

### 7.2 Prompt Types

- **Official Units**
  - Authoritative, declarative tone
  - Formal definitions permitted
- **Historical / Informal Units**
  - Chronological, author-specific descriptions
  - Explicit uncertainty and variability
  - Non-normative language ("used by", "commonly correlated with")

---

## 8. Local MCP and Remote LLM Interaction

### 8.1 Communication Model

- MCP server runs locally within SCODA
- LLMs are accessed via remote APIs
- SCODA acts as an **intermediary client**

LLMs:
- Do not access the local DB directly
- Do not receive API credentials

---

## 9. API Key Management

- API keys are managed exclusively by the SCODA runtime
- OS-level credential storage is recommended
- Keys are never stored in the DB or included in exports

---

## 10. Phased Implementation Plan

### Phase 1: Read-Only MCP
- Expose core query tools
- Enable evidence-grounded summarization

### Phase 2: UI Integration
- Add chat panel to SPA
- Enable context-aware narrative requests

### Phase 3: Export Integration
- Generate markdown or report-style outputs from LLM narratives

---

## 11. Non-Goals

- LLM-driven classification or definition
- Agentic planning or autonomous decision-making
- Write access to the database

---

## 12. Core Principles Summary

- **DB is truth**
- **MCP is access**
- **LLM is narration**
- **Snapshots are exports**

---

## 13. One-Sentence Summary

> SCODA wraps its existing local API as an MCP server, enabling language models to generate evidence-grounded narratives from historically explicit concept states without direct access to the underlying database.
