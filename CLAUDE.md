# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trilobase is a paleontological data repository focused on trilobite taxonomy. It contains structured reference data about trilobite families, genera, and nomenclature from the Paleozoic Era. Currently a data-only repository with no application code.

## Repository Structure

- **trilobite_genus_list.txt** - Main dataset (~5,095 genera) with format: `Genus AUTHORITY, YEAR [type specimen] Formation, Location; FAMILY; TIMEPERIOD.`
- **trilobite_family_list.txt** - Family taxonomy (~184 families) with constituent genera
- **trilobite_nomina_nuda.txt** - Invalid/unpublished names (~143 entries)
- **Jell_and_Adrain_2002_Literature_Cited.txt** - Bibliography (~2,292 references)

## Data Format Conventions

### Time Period Codes
- LCAM/MCAM/UCAM = Lower/Middle/Upper Cambrian
- LORD = Lower Ordovician
- LSIL/USIL = Lower/Upper Silurian
- LDEV/UDEV = Lower/Upper Devonian
- LPERM = Lower Permian

### Nomenclature Symbols
- `=` indicates synonymous names
- `/` indicates junior synonyms
- Brackets `[...]` contain type specimen information

### Authority Citations
Standard paleontological format: `AUTHOR, YEAR` (e.g., `LIEBERMAN, 1994`)

## Current State

This is a pure data repository with:
- No build system, package manager, or dependencies
- No test framework or CI/CD
- No application code

Data files can be parsed and converted to structured formats (CSV, JSON, database) for application development.
