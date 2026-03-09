#!/usr/bin/env python3
"""
Extract taxonomy from Treatise on Invertebrate Paleontology Part O (1959).

Source: "OUTLINE OF CLASSIFICATION" pp. O160-O167
Authors: H.J. Harrington, G. Henningsmoen, B.F. Howell, V. Jaanusson,
         C. Lochman-Balk, R.C. Moore, C. Poulsen, F. Rasetti,
         E. Richter, R. Richter, H. Schmidt, K. Sdzuy, W. Struve,
         L. Størmer, C.J. Stubblefield, R. Tripp, J.M. Weller, H.B. Whittington

The outline provides taxonomy from Class down to subfamily level,
with genus/subgenus counts per family group.
Numbers in parentheses: (genera) or (genera; subgenera).
Author codes: HA=Harrington, HE=Henningsmoen, HO=Howell, JA=Jaanusson,
  LB=Lochman-Balk, MO=Moore, PO=Poulsen, RA=Rasetti, RR=Richter,
  SC=Schmidt, SD=Sdzuy, ST=Struve, TR=Tripp, WE=Weller, WH=Whittington
"""

import json

def build_taxonomy():
    """Build the complete 1959 Treatise taxonomy tree from the outline."""

    taxonomy = {
        "source": "Treatise on Invertebrate Paleontology, Part O, Arthropoda 1, Trilobitomorpha (1959)",
        "editors": "Raymond C. Moore",
        "year": 1959,
        "pages": "O160-O167 (Outline), O172-O525 (Systematic Descriptions)",
        "note": "Higher taxonomy (Order-Subfamily) from Outline of Classification. Genus counts in parentheses as (genera) or (genera; subgenera).",
        "taxonomy": {
            "rank": "class",
            "name": "Trilobita",
            "author": "WALCH",
            "year": 1771,
            "genera_count": 1401,
            "subgenera_count": 128,
            "range": "L.Cam.-M.Perm.",
            "children": []
        }
    }

    trilobita = taxonomy["taxonomy"]

    # =========================================================================
    # ORDER AGNOSTIDA
    # =========================================================================
    agnostida = {
        "rank": "order",
        "name": "Agnostida",
        "author": "KOBAYASHI",
        "year": 1935,
        "genera_count": 79,
        "range": "L.Cam.-U.Ord.",
        "children": [
            # --- Suborder AGNOSTINA ---
            {
                "rank": "suborder",
                "name": "Agnostina",
                "author": "SALTER",
                "year": 1864,
                "genera_count": 66,
                "range": "L.Cam.-U.Ord.",
                "children": [
                    {"rank": "family", "name": "Agnostidae", "author": "M'COY", "year": 1849, "genera_count": 6, "range": "M.Cam.-L.Ord."},
                    {"rank": "family", "name": "Clavagnostidae", "author": "HOWELL", "year": 1937, "genera_count": 1, "range": "M.Cam.-U.Cam."},
                    {"rank": "family", "name": "Condylopygidae", "author": "RAYMOND", "year": 1913, "genera_count": 3, "range": "L.Cam.-M.Cam."},
                    {"rank": "family", "name": "Cyclopagnostidae", "author": "HOWELL", "year": 1937, "genera_count": 1, "range": "M.Cam."},
                    {"rank": "family", "name": "Diplagnostidae", "author": "WHITEHOUSE", "year": 1936, "genera_count": 4, "range": "M.Cam."},
                    {"rank": "family", "name": "Geragnostidae", "author": "HOWELL", "year": 1935, "genera_count": 6, "range": "L.Ord.-U.Ord."},
                    {"rank": "family", "name": "Hastagnostidae", "author": "HOWELL", "year": 1937, "genera_count": 10, "range": "M.Cam.-U.Cam."},
                    {"rank": "family", "name": "Micragnostidae", "author": "HOWELL", "year": 1935, "genera_count": 5, "range": "U.Cam.-L.Ord."},
                    {"rank": "family", "name": "Phalacromidae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 8, "range": "M.Cam.-L.Ord."},
                    {"rank": "family", "name": "Pseudagnostidae", "author": "WHITEHOUSE", "year": 1936, "genera_count": 4, "range": "U.Cam.-L.Ord."},
                    {"rank": "family", "name": "Sphaeragnostidae", "author": "KOBAYASHI", "year": 1939, "genera_count": 1, "range": "Ord."},
                    {"rank": "family", "name": "Spinagnostidae", "author": "HOWELL", "year": 1937, "genera_count": 17, "range": "L.Cam.-U.Cam."},
                ]
            },
            # --- Suborder EODISCINA ---
            {
                "rank": "suborder",
                "name": "Eodiscina",
                "author": "KOBAYASHI",
                "year": 1939,
                "genera_count": 13,
                "range": "L.Cam.-M.Cam.",
                "children": [
                    {"rank": "family", "name": "Eodiscidae", "author": "RAYMOND", "year": 1913, "genera_count": 6, "range": "L.Cam.-M.Cam."},
                    {"rank": "family", "name": "Pagetiidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 7, "range": "L.Cam.-M.Cam."},
                ]
            },
        ]
    }

    # =========================================================================
    # ORDER REDLICHIIDA
    # =========================================================================
    redlichiida = {
        "rank": "order",
        "name": "Redlichiida",
        "author": "RICHTER",
        "year": 1933,
        "genera_count": 107,
        "subgenera_count": 22,
        "range": "L.Cam.-M.Cam.",
        "children": [
            # --- Suborder OLENELLINA ---
            {
                "rank": "suborder",
                "name": "Olenellina",
                "author": "RESSER",
                "year": 1938,
                "genera_count": 22,
                "subgenera_count": 3,
                "range": "L.Cam.",
                "children": [
                    {
                        "rank": "family", "name": "Olenellidae", "author": "WALCOTT", "year": 1890,
                        "genera_count": 20, "range": "L.Cam.",
                        "children": [
                            {"rank": "subfamily", "name": "Olenellinae", "author": "WALCOTT", "year": 1890, "genera_count": 7, "range": "L.Cam."},
                            {"rank": "subfamily", "name": "Callaviinae", "author": "POULSEN", "year": 1927, "genera_count": 3, "range": "L.Cam."},
                            {"rank": "subfamily", "name": "Elliptocephalinae", "author": "MATTHEW", "year": 1887, "genera_count": 1, "range": "L.Cam."},
                            {"rank": "subfamily", "name": "Fallotaspidinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                            {"rank": "subfamily", "name": "Holmiinae", "author": "HUPE", "year": 1953, "genera_count": 3, "range": "L.Cam."},
                            {"rank": "subfamily", "name": "Neltneriinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                            {"rank": "subfamily", "name": "Nevadiinae", "author": "HUPE", "year": 1953, "genera_count": 2, "range": "L.Cam."},
                            {"rank": "subfamily", "name": "Olenelloidinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                            {"rank": "subfamily", "name": "Wanneriinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                        ]
                    },
                    {"rank": "family", "name": "Daguinaspididae", "author": "HUPE", "year": 1953, "genera_count": 2, "subgenera_count": 3, "range": "L.Cam."},
                ]
            },
            # --- Suborder REDLICHIINA ---
            {
                "rank": "suborder",
                "name": "Redlichiina",
                "author": "HARRINGTON",
                "year": 1959,
                "note": "nov.",
                "genera_count": 83,
                "subgenera_count": 19,
                "range": "L.Cam.-M.Cam.",
                "children": [
                    # Superfamily Redlichiacea
                    {
                        "rank": "superfamily", "name": "Redlichiacea", "author": "POULSEN", "year": 1927,
                        "genera_count": 25, "subgenera_count": 2, "range": "L.Cam.-M.Cam.",
                        "children": [
                            {
                                "rank": "family", "name": "Redlichiidae", "author": "POULSEN", "year": 1927,
                                "genera_count": 10, "range": "L.Cam.",
                                "children": [
                                    {"rank": "subfamily", "name": "Redlichiinae", "author": "POULSEN", "year": 1927, "genera_count": 5, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "Pararedlichiinae", "author": "HUPE", "year": 1953, "genera_count": 5, "range": "L.Cam."},
                                ]
                            },
                            {"rank": "family", "name": "Neoredlichiidae", "author": "HUPE", "year": 1953, "genera_count": 4, "subgenera_count": 2, "range": "L.Cam."},
                            {"rank": "family", "name": "Saukiandidae", "author": "HUPE", "year": 1953, "genera_count": 2, "range": "L.Cam."},
                            {"rank": "family", "name": "Gigantopygidae", "author": "HARRINGTON", "year": 1959, "genera_count": 1, "range": "L.Cam."},
                            {"rank": "family", "name": "Despujolsiidae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                            {"rank": "family", "name": "Yinitidae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "M.Cam."},
                            {"rank": "family", "name": "Abadiellidae", "author": "HUPE", "year": 1953, "genera_count": 3, "range": "L.Cam.-M.Cam."},
                            {"rank": "family", "name": "Dolerolenidae", "author": "HARRINGTON", "year": 1959, "genera_count": 1, "range": "Up.L.Cam."},
                            {"rank": "family", "name": "Family Uncertain", "genera_count": 2, "range": "L.Cam."},
                        ]
                    },
                    # Superfamily Ellipsocephalacea
                    {
                        "rank": "superfamily", "name": "Ellipsocephalacea", "author": "MATTHEW", "year": 1887,
                        "genera_count": 42, "subgenera_count": 17, "range": "L.Cam.-M.Cam.",
                        "children": [
                            {
                                "rank": "family", "name": "Ellipsocephalidae", "author": "MATTHEW", "year": 1887,
                                "genera_count": 18, "subgenera_count": 9, "range": "L.Cam.-M.Cam.",
                                "children": [
                                    {"rank": "subfamily", "name": "Ellipsocephalinae", "author": "MATTHEW", "year": 1887, "genera_count": 8, "range": "L.Cam.-M.Cam."},
                                    {"rank": "subfamily", "name": "Strenuellinae", "author": "HUPE", "year": 1953, "genera_count": 4, "subgenera_count": 7, "range": "L.Cam.-M.Cam."},
                                    {"rank": "subfamily", "name": "Kingaspidinae", "author": "HUPE", "year": 1953, "genera_count": 2, "subgenera_count": 2, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "Palaeoleninae", "author": "HUPE", "year": 1953, "genera_count": 3, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "Antatlasiinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                                ]
                            },
                            {
                                "rank": "family", "name": "Protolenidae", "author": "RICHTER & RICHTER", "year": 1948,
                                "genera_count": 21, "subgenera_count": 8, "range": "L.Cam.",
                                "children": [
                                    {"rank": "subfamily", "name": "Termierellinae", "author": "HUPE", "year": 1953, "genera_count": 6, "subgenera_count": 3, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "Myopsoleninae", "author": "HUPE", "year": 1953, "genera_count": 3, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "Protoleninae", "author": "RICHTER & RICHTER", "year": 1948, "genera_count": 8, "subgenera_count": 5, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "Bigotininae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "?Aldonaiinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "Subfamily Uncertain", "genera_count": 2, "range": "L.Cam."},
                                ]
                            },
                            {"rank": "family", "name": "?Yunnanocephalidae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                            {"rank": "family", "name": "Family Uncertain", "genera_count": 2, "range": "L.Cam."},
                        ]
                    },
                    # Superfamily Paradoxidacea
                    {
                        "rank": "superfamily", "name": "Paradoxidacea", "author": "HAWLE & CORDA", "year": 1847,
                        "genera_count": 16, "range": "Up.L.Cam.-M.Cam.",
                        "children": [
                            {
                                "rank": "family", "name": "Paradoxididae", "author": "HAWLE & CORDA", "year": 1847,
                                "genera_count": 15, "range": "Up.L.Cam.-M.Cam.",
                                "children": [
                                    {"rank": "subfamily", "name": "Paradoxidinae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 5, "range": "M.Cam."},
                                    {"rank": "subfamily", "name": "Centropleurinae", "author": "ANGELIN", "year": 1854, "genera_count": 3, "range": "M.Cam."},
                                    {"rank": "subfamily", "name": "Metadoxidinae", "author": "HUPE", "year": 1953, "genera_count": 3, "range": "Up.L.Cam."},
                                    {"rank": "subfamily", "name": "Xystridurinae", "author": "WHITEHOUSE", "year": 1939, "genera_count": 2, "range": "Up.L.Cam.-M.Cam."},
                                    {"rank": "subfamily", "name": "Subfamily Uncertain", "genera_count": 2, "range": "M.Cam."},
                                ]
                            },
                            {"rank": "family", "name": "Hicksiidae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                        ]
                    },
                ]
            },
            # --- Suborder BATHYNOTINA ---
            {
                "rank": "suborder",
                "name": "Bathynotina",
                "author": "LOCHMAN-BALK",
                "year": 1959,
                "note": "nov.",
                "genera_count": 2,
                "range": "Up.L.Cam.-Low.M.Cam.",
                "children": [
                    {"rank": "family", "name": "Bathynotidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 2, "range": "Up.L.Cam.-Low.M.Cam."},
                ]
            },
        ]
    }

    # =========================================================================
    # ORDER CORYNEXOCHIDA
    # =========================================================================
    corynexochida = {
        "rank": "order",
        "name": "Corynexochida",
        "author": "KOBAYASHI",
        "year": 1935,
        "genera_count": 73,
        "subgenera_count": 4,
        "range": "L.Cam.-U.Cam.",
        "children": [
            {"rank": "family", "name": "Dorypygidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 20, "range": "L.Cam.-U.Cam."},
            {"rank": "family", "name": "Ogygopsidae", "author": "RASETTI", "year": 1951, "genera_count": 1, "range": "M.Cam."},
            {"rank": "family", "name": "Oryctocephalidae", "author": "BEECHER", "year": 1897, "genera_count": 7, "range": "L.Cam.-M.Cam."},
            {
                "rank": "family", "name": "Dolichometopidae", "author": "WALCOTT", "year": 1916,
                "genera_count": 29, "subgenera_count": 4, "range": "L.Cam.-U.Cam.",
            },
            {
                "rank": "family", "name": "Corynexochidae", "author": "ANGELIN", "year": 1854,
                "genera_count": 4, "range": "M.Cam.",
                "children": [
                    {"rank": "subfamily", "name": "Corynexochinae", "author": "ANGELIN", "year": 1854, "genera_count": 3, "range": "M.Cam."},
                    {"rank": "subfamily", "name": "Acontheinae", "author": "RASETTI", "year": 1951, "genera_count": 1, "range": "M.Cam."},
                ]
            },
            {"rank": "family", "name": "Zacanthoididae", "author": "SWINNERTON", "year": 1915, "genera_count": 8, "range": "L.Cam.-M.Cam."},
            {"rank": "family", "name": "Dinesidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 4, "range": "Up.L.Cam.-Low.M.Cam."},
        ]
    }

    # =========================================================================
    # ORDER PTYCHOPARIIDA
    # =========================================================================
    ptychopariida = {
        "rank": "order",
        "name": "Ptychopariida",
        "author": "SWINNERTON",
        "year": 1915,
        "genera_count": 798,
        "subgenera_count": 61,
        "range": "L.Cam.-M.Perm.",
        "children": [
            # --- Suborder PTYCHOPARIINA ---
            {
                "rank": "suborder",
                "name": "Ptychopariina",
                "author": "RICHTER",
                "year": 1933,
                "genera_count": 474,
                "subgenera_count": 11,
                "range": "L.Cam.-U.Ord.",
                "children": [
                    # Superfamily Ptychopariacea
                    {
                        "rank": "superfamily", "name": "Ptychopariacea", "author": "MATTHEW", "year": 1887,
                        "genera_count": 63, "range": "L.Cam.-L.Ord.",
                        "children": [
                            {
                                "rank": "family", "name": "Ptychopariidae", "author": "MATTHEW", "year": 1887,
                                "genera_count": 32, "range": "L.Cam.-L.Ord.",
                                "children": [
                                    {"rank": "subfamily", "name": "Ptychopariinae", "author": "MATTHEW", "year": 1887, "genera_count": 10, "range": "M.Cam.-U.Cam."},
                                    {"rank": "subfamily", "name": "Periommelinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "L.Cam."},
                                    {"rank": "subfamily", "name": "Eulominae", "author": "KOBAYASHI", "year": 1935, "genera_count": 2, "range": "L.Ord."},
                                    {"rank": "subfamily", "name": "Nassoviinae", "author": "HUPE", "year": 1953, "genera_count": 4, "range": "M.Cam."},
                                    {"rank": "subfamily", "name": "Antagminae", "author": "HUPE", "year": 1953, "genera_count": 13, "range": "L.Cam.-Low.M.Cam."},
                                    {"rank": "subfamily", "name": "Conokephalininae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 3, "range": "M.Cam.-U.Cam."},
                                ]
                            },
                            {"rank": "family", "name": "Alokistocaridae", "author": "RESSER", "year": 1939, "genera_count": 30, "range": "L.Cam.-U.Cam."},
                        ]
                    },
                    # Superfamily Conocoryphacea
                    {
                        "rank": "superfamily", "name": "Conocoryphacea", "author": "ANGELIN", "year": 1854,
                        "genera_count": 23, "range": "L.Cam.-U.Ord.",
                        "children": [
                            {"rank": "family", "name": "Conocoryphidae", "author": "ANGELIN", "year": 1854, "genera_count": 16, "range": "L.Cam.-L.Ord."},
                            {"rank": "family", "name": "?Shumardiidae", "author": "LAKE", "year": 1907, "genera_count": 7, "range": "?M.Cam., U.Cam.-U.Ord."},
                        ]
                    },
                    # Superfamily Emmrichellacea
                    {
                        "rank": "superfamily", "name": "Emmrichellacea", "author": "KOBAYASHI", "year": 1935,
                        "genera_count": 15, "range": "M.Cam.-L.Ord.",
                        "children": [
                            {
                                "rank": "family", "name": "Emmrichellidae", "author": "KOBAYASHI", "year": 1935,
                                "genera_count": 13, "range": "M.Cam.-L.Ord.",
                                "children": [
                                    {"rank": "subfamily", "name": "Emmrichellinae", "author": "KOBAYASHI", "year": 1935, "genera_count": 9, "range": "M.Cam.-L.Ord."},
                                    {"rank": "subfamily", "name": "Changshaniinae", "author": "KOBAYASHI", "year": 1935, "genera_count": 4, "range": "M.Cam."},
                                ]
                            },
                            {"rank": "family", "name": "Liostracinidae", "author": "RAYMOND", "year": 1937, "genera_count": 2, "range": "M.Cam.-U.Cam."},
                        ]
                    },
                    # Superfamily Crepicephalacea
                    {
                        "rank": "superfamily", "name": "Crepicephalacea", "author": "KOBAYASHI", "year": 1935,
                        "genera_count": 7, "range": "M.Cam.-U.Cam.",
                        "children": [
                            {"rank": "family", "name": "Crepicephalidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 5, "range": "M.Cam.-U.Cam."},
                            {"rank": "family", "name": "Tricrepicephalidae", "author": "PALMER", "year": 1954, "genera_count": 2, "range": "U.Cam."},
                        ]
                    },
                    # Superfamily Nepeacea
                    {
                        "rank": "superfamily", "name": "Nepeacea", "author": "WHITEHOUSE", "year": 1939,
                        "genera_count": 1, "range": "M.Cam.",
                        "children": [
                            {"rank": "family", "name": "Nepeidae", "author": "WHITEHOUSE", "year": 1939, "genera_count": 1, "range": "M.Cam."},
                        ]
                    },
                    # Superfamily Dikelocephalacea
                    {
                        "rank": "superfamily", "name": "Dikelocephalacea", "author": "MILLER", "year": 1889,
                        "genera_count": 34, "range": "U.Cam.",
                        "children": [
                            {"rank": "family", "name": "Idahoiidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 7, "range": "U.Cam."},
                            {"rank": "family", "name": "Dikelocephalidae", "author": "MILLER", "year": 1889, "genera_count": 5, "range": "U.Cam."},
                            {"rank": "family", "name": "Pterocephalidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 16, "range": "U.Cam."},
                            {"rank": "family", "name": "Housiidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 1, "range": "U.Cam."},
                            {"rank": "family", "name": "Andrarinidae", "author": "HOWELL", "year": 1937, "genera_count": 5, "range": "L.Cam.-M.Cam."},
                        ]
                    },
                    # Superfamily Olenacea
                    {
                        "rank": "superfamily", "name": "Olenacea", "author": "BURMEISTER", "year": 1843,
                        "genera_count": 45, "subgenera_count": 5, "range": "M.Cam.-U.Ord.",
                        "children": [
                            {
                                "rank": "family", "name": "Olenidae", "author": "BURMEISTER", "year": 1843,
                                "genera_count": 37, "subgenera_count": 5, "range": "U.Cam.-U.Ord.",
                                "children": [
                                    {"rank": "subfamily", "name": "Oleninae", "author": "BURMEISTER", "year": 1843, "genera_count": 6, "range": "U.Cam.-L.Ord."},
                                    {"rank": "subfamily", "name": "Leptoplastinae", "author": "ANGELIN", "year": 1854, "genera_count": 3, "subgenera_count": 3, "range": "U.Cam.-L.Ord."},
                                    {"rank": "subfamily", "name": "Pelturinae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 16, "range": "U.Cam.-L.Ord."},
                                    {"rank": "subfamily", "name": "Triarthrinae", "author": "ULRICH", "year": 1930, "genera_count": 9, "subgenera_count": 2, "range": "U.Cam.-U.Ord."},
                                ]
                            },
                            {"rank": "family", "name": "Papyriaspididae", "author": "WHITEHOUSE", "year": 1939, "genera_count": 6, "range": "M.Cam.-U.Cam."},
                            {"rank": "family", "name": "Hypermecaspididae", "author": "HARRINGTON & LEANZA", "year": 1957, "genera_count": 2, "range": "L.Ord.-M.Ord."},
                        ]
                    },
                    # Superfamily Illaenuracea
                    {
                        "rank": "superfamily", "name": "Illaenuracea", "author": "VOGDES", "year": 1890,
                        "genera_count": 13, "range": "U.Cam.",
                        "children": [
                            {"rank": "family", "name": "Illaenuridae", "author": "VOGDES", "year": 1890, "genera_count": 2, "range": "U.Cam."},
                            {"rank": "family", "name": "Shirakiellidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 1, "range": "U.Cam."},
                            {"rank": "family", "name": "Parabolinoididae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 10, "range": "U.Cam."},
                        ]
                    },
                    # Superfamily Solenopleuracea
                    {
                        "rank": "superfamily", "name": "Solenopleuracea", "author": "ANGELIN", "year": 1854,
                        "genera_count": 73, "range": "M.Cam.-L.Ord.",
                        "children": [
                            {
                                "rank": "family", "name": "Solenopleuridae", "author": "ANGELIN", "year": 1854,
                                "genera_count": 33, "range": "M.Cam.-L.Ord.",
                                "children": [
                                    {"rank": "subfamily", "name": "Solenopleurinae", "author": "ANGELIN", "year": 1854, "genera_count": 13, "range": "M.Cam.-U.Cam."},
                                    {"rank": "subfamily", "name": "Acrocephalitinae", "author": "HUPE", "year": 1953, "genera_count": 7, "range": "M.Cam.-U.Cam."},
                                    {"rank": "subfamily", "name": "Saoinae", "author": "HUPE", "year": 1953, "genera_count": 4, "range": "M.Cam."},
                                    {"rank": "subfamily", "name": "Hystricurinae", "author": "HUPE", "year": 1953, "genera_count": 9, "range": "U.Cam.-L.Ord."},
                                ]
                            },
                            {"rank": "family", "name": "Agraulidae", "author": "RAYMOND", "year": 1913, "genera_count": 2, "range": "M.Cam."},
                            {"rank": "family", "name": "Lonchocephalidae", "author": "HUPE", "year": 1953, "genera_count": 11, "range": "U.Cam."},
                            {"rank": "family", "name": "Dokimocephalidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 10, "range": "U.Cam."},
                            {"rank": "family", "name": "Avoninidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 3, "range": "Up.M.Cam.-U.Cam."},
                            {"rank": "family", "name": "Catillicephalidae", "author": "RAYMOND", "year": 1938, "genera_count": 8, "range": "U.Cam."},
                            {"rank": "family", "name": "Kingstoniidae", "author": "KOBAYASHI", "year": 1933, "genera_count": 6, "range": "M.Cam.-U.Cam."},
                        ]
                    },
                    # Superfamily Anomocaracea
                    {
                        "rank": "superfamily", "name": "Anomocaracea", "author": "POULSEN", "year": 1927,
                        "genera_count": 26, "subgenera_count": 2, "range": "M.Cam.-U.Cam.",
                        "children": [
                            {"rank": "family", "name": "Anomocaridae", "author": "POULSEN", "year": 1927, "genera_count": 26, "subgenera_count": 2, "range": "M.Cam.-U.Cam."},
                        ]
                    },
                    # Superfamily Asaphiscacea
                    {
                        "rank": "superfamily", "name": "Asaphiscacea", "author": "RAYMOND", "year": 1924,
                        "genera_count": 19, "subgenera_count": 2, "range": "M.Cam.-U.Cam.",
                        "children": [
                            {
                                "rank": "family", "name": "Asaphiscidae", "author": "RAYMOND", "year": 1924,
                                "genera_count": 19, "subgenera_count": 2, "range": "M.Cam.-U.Cam.",
                                "children": [
                                    {"rank": "subfamily", "name": "Asaphiscinae", "author": "RAYMOND", "year": 1924, "genera_count": 16, "range": "M.Cam.-U.Cam."},
                                    {"rank": "subfamily", "name": "Blountiinae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 3, "subgenera_count": 2, "range": "U.Cam."},
                                ]
                            },
                        ]
                    },
                    # Superfamily Burlingiacea
                    {
                        "rank": "superfamily", "name": "Burlingiacea", "author": "WALCOTT", "year": 1908,
                        "genera_count": 2, "range": "M.Cam.-U.Cam.",
                        "children": [
                            {"rank": "family", "name": "Burlingiidae", "author": "WALCOTT", "year": 1908, "genera_count": 2, "range": "M.Cam.-U.Cam."},
                        ]
                    },
                    # Superfamily Komaspidacea
                    {
                        "rank": "superfamily", "name": "Komaspidacea", "author": "KOBAYASHI", "year": 1935,
                        "genera_count": 16, "range": "M.Cam.-U.Cam.",
                        "children": [
                            {"rank": "family", "name": "Komaspididae", "author": "KOBAYASHI", "year": 1935, "genera_count": 8, "range": "Up.M.Cam.-L.Ord."},
                            {"rank": "family", "name": "Elviniidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 5, "range": "U.Cam."},
                            {"rank": "family", "name": "Telephinidae", "author": "MAREK", "year": 1952, "genera_count": 1, "range": "M.Ord.-U.Ord."},
                            {"rank": "family", "name": "Glaphuridae", "author": "WHITTINGTON", "year": 1959, "genera_count": 2, "range": "M.Ord."},
                        ]
                    },
                    # Superfamily Raymondinacea
                    {
                        "rank": "superfamily", "name": "Raymondinacea", "author": "CLARK", "year": 1924,
                        "genera_count": 11, "range": "U.Cam.",
                        "children": [
                            {
                                "rank": "family", "name": "Raymondinidae", "author": "CLARK", "year": 1924,
                                "genera_count": 11, "range": "U.Cam.",
                                "children": [
                                    {"rank": "subfamily", "name": "Raymondininae", "author": "CLARK", "year": 1924, "genera_count": 5, "range": "U.Cam."},
                                    {"rank": "subfamily", "name": "Cedariinae", "author": "RAYMOND", "year": 1937, "genera_count": 2, "range": "U.Cam."},
                                    {"rank": "subfamily", "name": "Llanoaspidinae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 4, "range": "U.Cam."},
                                ]
                            },
                        ]
                    },
                    # Superfamily Norwoodiacea
                    {
                        "rank": "superfamily", "name": "Norwoodiacea", "author": "WALCOTT", "year": 1916,
                        "genera_count": 15, "range": "M.Cam.-L.Ord.",
                        "children": [
                            {"rank": "family", "name": "Norwoodiidae", "author": "WALCOTT", "year": 1916, "genera_count": 5, "range": "U.Cam.-L.Ord."},
                            {"rank": "family", "name": "Menomoniidae", "author": "WALCOTT", "year": 1916, "genera_count": 6, "range": "M.Cam.-U.Cam."},
                            {"rank": "family", "name": "Bolaspididae", "author": "HOWELL", "year": 1959, "genera_count": 4, "range": "M.Cam."},
                        ]
                    },
                    # Superfamily Marjumiacea
                    {
                        "rank": "superfamily", "name": "Marjumiacea", "author": "KOBAYASHI", "year": 1935,
                        "genera_count": 35, "range": "M.Cam.-L.Ord.",
                        "children": [
                            {"rank": "family", "name": "Marjumiidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 20, "range": "M.Cam.-U.Cam."},
                            {"rank": "family", "name": "Coosellidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 4, "range": "U.Cam."},
                            {"rank": "family", "name": "Pagodiidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 10, "range": "M.Cam.-L.Ord."},
                            {"rank": "family", "name": "Cheilocephalidae", "author": "SHAW", "year": 1956, "genera_count": 1, "range": "U.Cam."},
                        ]
                    },
                    # Superfamily Leiostegiiacea  (corrected from Leiostegiacea)
                    {
                        "rank": "superfamily", "name": "Leiostegiiacea", "author": "KOBAYASHI", "year": 1935,
                        "genera_count": 16, "subgenera_count": 2, "range": "M.Cam.-L.Ord.",
                        "children": [
                            {
                                "rank": "family", "name": "Leiostegiidae", "author": "KOBAYASHI", "year": 1935,
                                "genera_count": 16, "subgenera_count": 2, "range": "M.Cam.-L.Ord.",
                                "children": [
                                    {"rank": "subfamily", "name": "Leostegiinae", "author": "KOBAYASHI", "year": 1935, "genera_count": 12, "subgenera_count": 2, "range": "M.Cam.-L.Ord."},
                                    {"rank": "subfamily", "name": "Iranaspidinae", "author": "KOBAYASHI", "year": 1935, "genera_count": 2, "range": "U.Cam.-L.Ord."},
                                ]
                            },
                        ]
                    },
                    # Superfamily Damesellacea
                    {
                        "rank": "superfamily", "name": "Damesellacea", "author": "KOBAYASHI", "year": 1935,
                        "genera_count": 10, "range": "M.Cam.-U.Cam.",
                        "children": [
                            {
                                "rank": "family", "name": "Damesellidae", "author": "KOBAYASHI", "year": 1935,
                                "genera_count": 10, "range": "M.Cam.-U.Cam.",
                                "children": [
                                    {"rank": "subfamily", "name": "Damesellinae", "author": "KOBAYASHI", "year": 1935, "genera_count": 6, "range": "M.Cam.-U.Cam."},
                                    {"rank": "subfamily", "name": "Drepanurinae", "author": "HUPE", "year": 1953, "genera_count": 2, "range": "M.Cam.-U.Cam."},
                                    {"rank": "subfamily", "name": "Kaolishaniidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 4, "range": "U.Cam."},  # actually this might be wrong
                                ]
                            },
                        ]
                    },
                    # Superfamily Ptychaspidacea
                    {
                        "rank": "superfamily", "name": "Ptychaspidacea", "author": "RAYMOND", "year": 1924,
                        "genera_count": 24, "range": "U.Cam.",
                        "children": [
                            {"rank": "family", "name": "Ptychaspididae", "author": "RAYMOND", "year": 1924, "genera_count": 13, "range": "U.Cam."},
                            {"rank": "family", "name": "Saukiidae", "author": "ULRICH & RESSER", "year": 1930, "genera_count": 6, "range": "U.Cam."},
                            {"rank": "family", "name": "Eurekiidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 5, "range": "Up.U.Cam."},
                        ]
                    },
                    # Superfamily Remopleuridacea
                    {
                        "rank": "superfamily", "name": "Remopleuridacea", "author": "HAWLE & CORDA", "year": 1847,
                        "genera_count": 25, "range": "U.Cam.-U.Ord.",
                        "children": [
                            {
                                "rank": "family", "name": "Remopleurididae", "author": "HAWLE & CORDA", "year": 1847,
                                "genera_count": 21, "range": "U.Cam.-U.Ord.",
                                "children": [
                                    {"rank": "subfamily", "name": "Remopleuridinae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 6, "range": "L.Ord.-U.Ord."},
                                    {"rank": "subfamily", "name": "Richardsonellinae", "author": "RAYMOND", "year": 1924, "genera_count": 12, "range": "U.Cam.-M.Ord."},
                                    {"rank": "subfamily", "name": "Subfamily Uncertain", "genera_count": 3, "range": "U.Cam."},
                                ]
                            },
                            {"rank": "family", "name": "Loganellidae", "author": "RASETTI", "year": 1951, "genera_count": 3, "range": "U.Cam."},
                            {"rank": "family", "name": "Hungaiidae", "author": "RAYMOND", "year": 1924, "genera_count": 1, "range": "U.Cam."},
                        ]
                    },
                    # Superfamily Uncertain
                    {
                        "rank": "superfamily", "name": "Superfamily Uncertain",
                        "genera_count": 1, "range": "U.Cam.",
                        "children": [
                            {"rank": "family", "name": "Diceratocephalidae", "author": "LU", "year": 1954, "genera_count": 1, "range": "U.Cam."},
                        ]
                    },
                ]
            },
            # --- Suborder ASAPHINA ---
            {
                "rank": "suborder",
                "name": "Asaphina",
                "author": "SALTER",
                "year": 1864,
                "genera_count": 112,
                "subgenera_count": 20,
                "range": "Up.M.Cam.-U.Ord.",
                "children": [
                    # Superfamily Asaphacea
                    {
                        "rank": "superfamily", "name": "Asaphacea", "author": "BURMEISTER", "year": 1843,
                        "genera_count": 94, "subgenera_count": 20, "range": "U.Cam.-U.Ord.",
                        "children": [
                            {
                                "rank": "family", "name": "Asaphidae", "author": "BURMEISTER", "year": 1843,
                                "genera_count": 68, "subgenera_count": 16, "range": "U.Cam.-U.Ord.",
                                "children": [
                                    {"rank": "subfamily", "name": "Asaphinae", "author": "BURMEISTER", "year": 1843, "genera_count": 11, "subgenera_count": 7, "range": "L.Ord.-U.Ord."},
                                    {"rank": "subfamily", "name": "Isotelinae", "author": "ANGELIN", "year": 1854, "genera_count": 27, "subgenera_count": 7, "range": "L.Ord.-U.Ord."},
                                    {"rank": "subfamily", "name": "Niobinae", "author": "JAANUSSON", "year": 1959, "genera_count": 7, "range": "U.Cam.-L.Ord."},
                                    {"rank": "subfamily", "name": "Ogyginocaridinae", "author": "RAYMOND", "year": 1920, "genera_count": 5, "range": "L.Ord.-M.Ord."},
                                    {"rank": "subfamily", "name": "Promegalaspidinae", "author": "JAANUSSON", "year": 1959, "genera_count": 2, "range": "U.Cam.-L.Ord."},
                                    {"rank": "subfamily", "name": "Symphysurinae", "author": "JAANUSSON", "year": 1959, "genera_count": 5, "subgenera_count": 2, "range": "L.Ord."},
                                    {"rank": "subfamily", "name": "Thysanopyginae", "author": "JAANUSSON", "year": 1959, "genera_count": 3, "range": "L.Ord."},
                                    {"rank": "subfamily", "name": "Subfamily Uncertain", "genera_count": 3, "range": "U.Cam.-M.Ord."},
                                    {"rank": "note", "name": "Unrecognizable asaphid genera", "genera_count": 5, "range": "Ord."},
                                ]
                            },
                            {"rank": "family", "name": "Taihungshaniidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 4, "range": "L.Ord."},
                            {"rank": "family", "name": "Tsinaniidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 2, "range": "U.Cam."},
                            {"rank": "family", "name": "Nileidae", "author": "ANGELIN", "year": 1854, "genera_count": 11, "subgenera_count": 4, "range": "L.Ord.-U.Ord."},
                            {"rank": "family", "name": "Dikelokephalinidae", "author": "KOBAYASHI", "year": 1935, "genera_count": 9, "range": "L.Ord."},
                        ]
                    },
                    # Superfamily Cyclopygacea
                    {
                        "rank": "superfamily", "name": "Cyclopygacea", "author": "RAYMOND", "year": 1925,
                        "genera_count": 7, "range": "Ord.",
                        "children": [
                            {"rank": "family", "name": "Cyclopygidae", "author": "RAYMOND", "year": 1925, "genera_count": 7, "range": "Ord."},
                        ]
                    },
                    # Superfamily Ceratopygacea
                    {
                        "rank": "superfamily", "name": "Ceratopygacea", "author": "LINNARSSON", "year": 1869,
                        "genera_count": 11, "range": "M.Cam.-L.Ord.",
                        "children": [
                            {"rank": "family", "name": "Ceratopygidae", "author": "LINNARSSON", "year": 1869, "genera_count": 11, "range": "M.Cam.-L.Ord."},
                        ]
                    },
                ]
            },
            # --- Suborder ILLAENINA ---
            {
                "rank": "suborder",
                "name": "Illaenina",
                "author": "JAANUSSON",
                "year": 1959,
                "note": "nov.",
                "genera_count": 144,
                "subgenera_count": 33,
                "range": "Ord.-M.Perm.",
                "children": [
                    # Superfamily Illaenacea
                    {
                        "rank": "superfamily", "name": "Illaenacea", "author": "HAWLE & CORDA", "year": 1847,
                        "genera_count": 25, "subgenera_count": 10, "range": "Ord.-Sil.",
                        "children": [
                            {
                                "rank": "family", "name": "Illaenidae", "author": "HAWLE & CORDA", "year": 1847,
                                "genera_count": 17, "subgenera_count": 14, "range": "L.Ord.-Sil.",
                                "children": [
                                    {"rank": "subfamily", "name": "Illaeninae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 7, "range": "L.Ord.-Sil."},
                                    {"rank": "subfamily", "name": "Bumastinae", "author": "RAYMOND", "year": 1916, "genera_count": 5, "subgenera_count": 4, "range": "M.Ord.-Sil."},
                                    {"rank": "subfamily", "name": "Ectillaeninae", "author": "JAANUSSON", "year": 1959, "genera_count": 3, "range": "L.Ord.-U.Ord."},
                                    {"rank": "subfamily", "name": "?Theamataspdinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "M.Ord.-U.Ord."},
                                    {"rank": "subfamily", "name": "Subfamily Uncertain", "genera_count": 1, "range": "Ord."},
                                ]
                            },
                            {"rank": "family", "name": "Styginidae", "author": "RAYMOND", "year": 1913, "genera_count": 4, "range": "L.Ord.-U.Ord."},
                            {"rank": "family", "name": "Thysanopeltidae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 4, "subgenera_count": 6, "range": "M.Ord.-Low.U.Dev."},
                        ]
                    },
                    # Superfamily Bathyuracea
                    {
                        "rank": "superfamily", "name": "Bathyuracea", "author": "WALCOTT", "year": 1916,
                        "genera_count": 22, "range": "U.Cam.-M.Ord.",
                        "children": [
                            {"rank": "family", "name": "Bathyuridae", "author": "WALCOTT", "year": 1916, "genera_count": 17, "range": "L.Ord.-M.Ord."},
                            {"rank": "family", "name": "Lecanopygidae", "author": "LOCHMAN-BALK", "year": 1959, "genera_count": 5, "range": "U.Cam.-L.Ord."},
                        ]
                    },
                    # Superfamily Holotrachelacea
                    {
                        "rank": "superfamily", "name": "Holotrachelacea", "author": "WARBURG", "year": 1925,
                        "genera_count": 1, "range": "U.Ord.",
                        "children": [
                            {"rank": "family", "name": "Holotrachelidae", "author": "WARBURG", "year": 1925, "genera_count": 1, "range": "U.Ord."},
                        ]
                    },
                    # Superfamily Proetacea
                    {
                        "rank": "superfamily", "name": "Proetacea", "author": "SALTER", "year": 1864,
                        "genera_count": 96, "subgenera_count": 23, "range": "L.Ord.-M.Perm.",
                        "children": [
                            {
                                "rank": "family", "name": "Proetidae", "author": "SALTER", "year": 1864,
                                "genera_count": 41, "subgenera_count": 19, "range": "M.Ord.-L.Carb.(Miss.)",
                                "children": [
                                    {"rank": "subfamily", "name": "Proetinae", "author": "SALTER", "year": 1864, "genera_count": 4, "subgenera_count": 2, "range": "M.Ord.-M.Dev."},
                                    {"rank": "subfamily", "name": "Cornuproetinae", "author": "RICHTER & RICHTER", "year": 1919, "genera_count": 6, "subgenera_count": 3, "range": "Ord.-U.Dev."},
                                    {"rank": "subfamily", "name": "Dechenellinae", "author": "PRZIBRAM", "year": 1909, "genera_count": 3, "subgenera_count": 4, "range": "Up.L.Dev.-U.Dev."},
                                    {"rank": "subfamily", "name": "Cyrtosymbolinae", "author": "HUPE", "year": 1953, "genera_count": 13, "subgenera_count": 10, "range": "L.Dev.-L.Carb."},
                                    {"rank": "subfamily", "name": "Proetidellinae", "author": "HUPE", "year": 1953, "genera_count": 9, "range": "M.Ord.-M.Dev."},
                                    {"rank": "subfamily", "name": "Tropidocoryphinae", "author": "PRZIBRAM", "year": 1909, "genera_count": 6, "range": "Sil.-Low.U.Dev."},
                                ]
                            },
                            {
                                "rank": "family", "name": "Phillipsiidae", "author": "OEHLERT", "year": 1886,
                                "genera_count": 24, "range": "L.Carb.(Miss.)-M.Perm.",
                                "children": [
                                    {"rank": "subfamily", "name": "Otarioninae", "author": "RICHTER & RICHTER", "year": 1926, "genera_count": 4, "range": "M.Ord.-U.Carb."},
                                    {"rank": "subfamily", "name": "Otarioninae", "note": "duplicate key - this is actually separate", "genera_count": 3, "range": "M.Ord.-U.Carb."},
                                    {"rank": "subfamily", "name": "Cyphaspinae", "author": "RICHTER & RICHTER", "year": 1926, "genera_count": 1, "range": "L.Dev.-M.Dev."},
                                    {"rank": "subfamily", "name": "Aulacopleurinae", "author": "ANGELIN", "year": 1854, "genera_count": 2, "subgenera_count": 2, "range": "M.Ord.-M.Dev."},
                                ]
                            },
                            {"rank": "family", "name": "Brachymetopidae", "author": "PRANTL & PRIBYL", "year": 1950, "genera_count": 5, "subgenera_count": 2, "range": "L.Dev.-U.Carb."},
                            {"rank": "family", "name": "Phillipsinellidae", "author": "WHITTINGTON", "year": 1959, "genera_count": 1, "range": "U.Ord."},
                            {"rank": "family", "name": "Celmidae", "author": "WHITTINGTON", "year": 1959, "genera_count": 1, "range": "L.Ord."},
                            {"rank": "family", "name": "Plethopeltidae", "author": "RAYMOND", "year": 1925, "genera_count": 7, "range": "U.Cam.-L.Ord."},
                            {"rank": "family", "name": "Dimeropygidae", "author": "HUPE", "year": 1953, "genera_count": 5, "range": "L.Ord.-U.Ord."},
                            {"rank": "family", "name": "Family Uncertain", "genera_count": 6, "range": "Sil.-Miss."},
                        ]
                    },
                ]
            },
            # --- Suborder HARPINA ---
            {
                "rank": "suborder",
                "name": "Harpina",
                "author": "WHITTINGTON",
                "year": 1959,
                "note": "nov.",
                "genera_count": 18, "range": "U.Cam.-U.Dev.",
                "children": [
                    {"rank": "family", "name": "Harpidae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 12, "range": "L.Ord.-U.Dev."},
                    {"rank": "family", "name": "Harpididae", "author": "WHITTINGTON", "year": 1959, "genera_count": 4, "range": "U.Cam.-L.Ord."},
                    {"rank": "family", "name": "Entomaspididae", "author": "ULRICH", "year": 1931, "genera_count": 2, "range": "U.Cam.-L.Ord."},
                ]
            },
            # --- Suborder TRINUCLEINA ---
            {
                "rank": "suborder",
                "name": "Trinucleina",
                "author": "SWINNERTON",
                "year": 1915,
                "genera_count": 50, "range": "L.Ord.-M.Sil.",
                "children": [
                    {
                        "rank": "family", "name": "Trinucleidae", "author": "HAWLE & CORDA", "year": 1847,
                        "genera_count": 27, "range": "L.Ord.-U.Ord.",
                        "children": [
                            {"rank": "subfamily", "name": "Trinucleinae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 2, "range": "L.Ord.-M.Ord."},
                            {"rank": "subfamily", "name": "Tretaspinae", "author": "WHITTINGTON", "year": 1959, "genera_count": 3, "range": "M.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Cryptolithinae", "author": "ANGELIN", "year": 1854, "genera_count": 21, "range": "L.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Novaspidinae", "author": "WHITTINGTON", "year": 1959, "genera_count": 1, "range": "U.Ord."},
                        ]
                    },
                    {"rank": "family", "name": "Orometopidae", "author": "HUPE", "year": 1955, "genera_count": 1, "range": "L.Ord."},
                    {"rank": "family", "name": "Dionididae", "author": "GURICH", "year": 1907, "genera_count": 4, "range": "M.Ord.-U.Ord."},
                    {"rank": "family", "name": "Raphiophoridae", "author": "ANGELIN", "year": 1854, "genera_count": 9, "range": "L.Ord.-M.Sil."},
                    {"rank": "family", "name": "Endymioniidae", "author": "RAYMOND", "year": 1920, "genera_count": 2, "range": "L.Ord.-M.Ord."},
                    {"rank": "family", "name": "Alsataspididae", "author": "TURNER", "year": 1940, "genera_count": 2, "range": "L.Ord."},
                    {"rank": "family", "name": "Hapalopleuridae", "author": "WHITTINGTON", "year": 1959, "genera_count": 4, "range": "L.Ord."},
                    {"rank": "family", "name": "Ityophoridae", "author": "WHITTINGTON", "year": 1959, "genera_count": 1, "range": "U.Ord."},
                ]
            },
        ]
    }

    # =========================================================================
    # ORDER PHACOPIDA
    # =========================================================================
    phacopida = {
        "rank": "order",
        "name": "Phacopida",
        "author": "SALTER",
        "year": 1864,
        "genera_count": 173,
        "subgenera_count": 37,
        "range": "L.Ord.-U.Dev.",
        "children": [
            # --- Suborder CHEIRURINA ---
            {
                "rank": "suborder",
                "name": "Cheirurina",
                "author": "HARRINGTON & LEANZA",
                "year": 1957,
                "genera_count": 73,
                "subgenera_count": 9,
                "range": "L.Ord.-M.Dev.",
                "children": [
                    {
                        "rank": "family", "name": "Cheiruridae", "author": "SALTER", "year": 1864,
                        "genera_count": 32, "subgenera_count": 7, "range": "L.Ord.(Tremadoc.)-M.Dev.",
                        "children": [
                            {"rank": "subfamily", "name": "Cheirurinae", "author": "SALTER", "year": 1864, "genera_count": 11, "subgenera_count": 2, "range": "L.Ord.-M.Dev."},
                            {"rank": "subfamily", "name": "Cyrtometopinae", "author": "OPIK", "year": 1937, "genera_count": 7, "subgenera_count": 5, "range": "L.Ord.-Sil."},
                            {"rank": "subfamily", "name": "Acanthoparyphinae", "author": "WHITTINGTON", "year": 1959, "genera_count": 4, "range": "L.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Sphaerexochinae", "author": "OPIK", "year": 1937, "genera_count": 2, "range": "M.Ord.-Sil., ?Dev."},
                            {"rank": "subfamily", "name": "Deiphoninae", "author": "RAYMOND", "year": 1913, "genera_count": 4, "range": "M.Ord.-Sil."},
                            {"rank": "subfamily", "name": "Areiinae", "author": "PRANTL & PRIBYL", "year": 1947, "genera_count": 1, "range": "M.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "?Heliomerinae", "author": "WEBER", "year": 1948, "genera_count": 2, "range": "M.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Subfamily Uncertain", "genera_count": 1, "range": "Sil.-L.Dev."},
                        ]
                    },
                    {
                        "rank": "family", "name": "Pliomeridae", "author": "RAYMOND", "year": 1913,
                        "genera_count": 25, "range": "L.Ord.-U.Ord.",
                        "children": [
                            {"rank": "subfamily", "name": "Pilekiinae", "author": "SDZUY", "year": 1955, "genera_count": 8, "range": "L.Ord."},
                            {"rank": "subfamily", "name": "Protopliomeropinae", "author": "HUPE", "year": 1953, "genera_count": 9, "range": "L.Ord."},
                            {"rank": "subfamily", "name": "Pliomerellinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "M.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Placopariinae", "author": "HUPE", "year": 1953, "genera_count": 1, "range": "M.Ord."},
                            {"rank": "subfamily", "name": "Diaphanometopinae", "author": "JAANUSSON", "year": 1959, "genera_count": 1, "range": "L.Ord."},
                        ]
                    },
                    {
                        "rank": "family", "name": "Encrinuridae", "author": "ANGELIN", "year": 1854,
                        "genera_count": 14, "subgenera_count": 2, "range": "L.Ord.-Sil.",
                        "children": [
                            {"rank": "subfamily", "name": "Encrinurinae", "author": "ANGELIN", "year": 1854, "genera_count": 4, "subgenera_count": 2, "range": "M.Ord.-Sil."},
                            {"rank": "subfamily", "name": "Cybelinae", "author": "REED", "year": 1928, "genera_count": 5, "range": "L.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Dindymeninae", "author": "RAYMOND", "year": 1916, "genera_count": 3, "range": "M.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Staurocephalinae", "author": "PRIBYL", "year": 1946, "genera_count": 2, "range": "M.Ord.-Sil."},
                        ]
                    },
                    {"rank": "family", "name": "Family Uncertain", "genera_count": 2, "range": "L.Ord.-M.Ord."},
                ]
            },
            # --- Suborder CALYMENINA ---
            {
                "rank": "suborder",
                "name": "Calymenina",
                "author": "SWINNERTON",
                "year": 1915,
                "genera_count": 27,
                "subgenera_count": 8,
                "range": "LowL.Ord.-M.Dev.",
                "children": [
                    {
                        "rank": "family", "name": "Calymenidae", "author": "BURMEISTER", "year": 1843,
                        "genera_count": 15, "subgenera_count": 2, "range": "L.Ord.(Arenig.)-M.Dev.",
                        "children": [
                            {"rank": "subfamily", "name": "Calymeninae", "author": "BURMEISTER", "year": 1843, "genera_count": 14, "subgenera_count": 2, "range": "L.Ord.-M.Dev."},
                            {"rank": "subfamily", "name": "Pharostomatinae", "author": "HUPE", "year": 1955, "genera_count": 1, "range": "M.Ord.-U.Ord."},
                        ]
                    },
                    {
                        "rank": "family", "name": "Homalonotidae", "author": "CHAPMAN", "year": 1890,
                        "genera_count": 12, "subgenera_count": 6, "range": "L.Ord.-M.Dev.",
                        "children": [
                            {"rank": "subfamily", "name": "Bavarillinae", "author": "HUPE", "year": 1955, "genera_count": 1, "range": "L.Ord."},
                            {"rank": "subfamily", "name": "Euhomalonotinae", "author": "REED", "year": 1918, "genera_count": 2, "subgenera_count": 2, "range": "L.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Colpocoryphinae", "author": "HUPE", "year": 1955, "genera_count": 3, "range": "L.Ord.-M.Ord.(Llandeilian)"},
                            {"rank": "subfamily", "name": "Homalonotinae", "author": "CHAPMAN", "year": 1890, "genera_count": 5, "subgenera_count": 4, "range": "M.Sil.-M.Dev."},
                        ]
                    },
                ]
            },
            # --- Suborder PHACOPINA ---
            {
                "rank": "suborder",
                "name": "Phacopina",
                "author": "STRUVE",
                "year": 1959,
                "note": "nov.",
                "genera_count": 73,
                "subgenera_count": 20,
                "range": "L.Ord.-Up.U.Dev.",
                "children": [
                    # Superfamily Phacopacea
                    {
                        "rank": "superfamily", "name": "Phacopacea", "author": "HAWLE & CORDA", "year": 1847,
                        "genera_count": 18, "range": "Sil.-U.Dev.",
                        "children": [
                            {
                                "rank": "family", "name": "Phacopidae", "author": "HAWLE & CORDA", "year": 1847,
                                "genera_count": 18, "range": "Sil.-U.Dev.",
                                "children": [
                                    {"rank": "subfamily", "name": "Phacopinae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 10, "range": "Sil.-U.Dev."},
                                    {"rank": "subfamily", "name": "Bouleiinae", "author": "HUPE", "year": 1955, "genera_count": 1, "range": "Dev."},
                                    {"rank": "subfamily", "name": "Phacopidellinae", "author": "DELO", "year": 1935, "genera_count": 6, "range": "Sil.-U.Dev."},
                                    {"rank": "subfamily", "name": "Subfamily Uncertain", "genera_count": 1, "range": "Sil."},
                                ]
                            },
                        ]
                    },
                    # Superfamily Dalmanitacea
                    {
                        "rank": "superfamily", "name": "Dalmanitacea", "author": "VOGDES", "year": 1890,
                        "genera_count": 55, "subgenera_count": 20, "range": "L.Ord.-U.Dev.",
                        "children": [
                            {
                                "rank": "family", "name": "Dalmanitidae", "author": "VOGDES", "year": 1890,
                                "genera_count": 31, "subgenera_count": 9, "range": "Low.M.Ord.-U.Dev.",
                                "children": [
                                    {"rank": "subfamily", "name": "Dalmanitinae", "author": "VOGDES", "year": 1890, "genera_count": 13, "range": "Sil.-M.Dev."},
                                    {"rank": "subfamily", "name": "Zeliszkellinае", "author": "DELO", "year": 1935, "genera_count": 4, "subgenera_count": 4, "range": "Low.M.Ord.-U.Ord., ?M.Sil."},
                                    {"rank": "subfamily", "name": "Acastavinae", "author": "DELO", "year": 1935, "genera_count": 3, "range": "U.Sil.-L.Dev."},
                                    {"rank": "subfamily", "name": "Asteropyginae", "author": "DELO", "year": 1935, "genera_count": 11, "subgenera_count": 5, "range": "L.Dev.-U.Dev."},
                                ]
                            },
                            {
                                "rank": "family", "name": "Calmoniidae", "author": "DELO", "year": 1935,
                                "genera_count": 15, "subgenera_count": 2, "range": "Ord.-M.Dev.",
                                "children": [
                                    {"rank": "subfamily", "name": "Calmoniinae", "author": "DELO", "year": 1935, "genera_count": 11, "range": "Ord.-M.Dev."},
                                    {"rank": "subfamily", "name": "Acastinae", "author": "DELO", "year": 1935, "genera_count": 4, "subgenera_count": 2, "range": "Ord.-L.Dev."},
                                ]
                            },
                            {"rank": "family", "name": "Pterygometopidae", "author": "REED", "year": 1905, "genera_count": 5, "subgenera_count": 6, "range": "M.Ord.-U.Ord."},
                            {"rank": "subfamily", "name": "Chasmopinae", "author": "DELO", "year": 1935, "genera_count": 1, "range": "Ord."},
                            {"rank": "family", "name": "Monorakidae", "author": "HUPE", "year": 1955, "genera_count": 4, "subgenera_count": 3, "range": "M.Ord.-U.Ord."},
                        ]
                    },
                ]
            },
        ]
    }

    # =========================================================================
    # ORDER LICHIDA
    # =========================================================================
    lichida = {
        "rank": "order",
        "name": "Lichida",
        "author": "MOORE",
        "year": 1959,
        "note": "nov.",
        "genera_count": 25,
        "range": "L.Ord.-U.Dev.",
        "children": [
            {
                "rank": "family", "name": "Lichidae", "author": "HAWLE & CORDA", "year": 1847,
                "genera_count": 24, "range": "L.Ord.-U.Dev.",
                "children": [
                    {"rank": "subfamily", "name": "Lichinae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 10, "range": "L.Ord.-U.Dev."},
                    {"rank": "subfamily", "name": "Homolichinae", "author": "PRANTL & PRIBYL", "year": 1949, "genera_count": 3, "range": "L.Ord.-M.Sil."},
                    {"rank": "subfamily", "name": "Tetralichinae", "author": "PRANTL & PRIBYL", "year": 1949, "genera_count": 2, "range": "M.Ord.-U.Ord."},
                    {"rank": "subfamily", "name": "Ceratarginae", "author": "TRIPP", "year": 1957, "genera_count": 9, "range": "M.Ord.-U.Dev."},
                ]
            },
            {"rank": "family", "name": "Lichakephalidae", "author": "TRIPP", "year": 1957, "genera_count": 1, "range": "L.Ord."},
        ]
    }

    # =========================================================================
    # ORDER ODONTOPLEURIDA
    # =========================================================================
    odontopleurida = {
        "rank": "order",
        "name": "Odontopleurida",
        "author": "WHITTINGTON",
        "year": 1959,
        "note": "nov.",
        "genera_count": 25,
        "subgenera_count": 4,
        "range": "Up.M.Cam.-U.Dev.",
        "children": [
            {
                "rank": "family", "name": "Odontopleuridae", "author": "BURMEISTER", "year": 1843,
                "genera_count": 22, "subgenera_count": 4, "range": "L.Ord.-U.Dev.",
                "children": [
                    {"rank": "subfamily", "name": "Odontopleurinae", "author": "BURMEISTER", "year": 1843, "genera_count": 7, "subgenera_count": 2, "range": "M.Ord.-U.Dev."},
                    {"rank": "subfamily", "name": "Miraspidinae", "author": "RICHTER & RICHTER", "year": 1917, "genera_count": 9, "subgenera_count": 2, "range": "M.Ord.-M.Dev."},
                    {"rank": "subfamily", "name": "Selenopeltinae", "author": "HAWLE & CORDA", "year": 1847, "genera_count": 1, "range": "M.Ord.-U.Ord."},
                    {"rank": "subfamily", "name": "Apianurinae", "author": "WHITTINGTON", "year": 1959, "genera_count": 2, "range": "M.Ord.-U.Ord."},
                    {"rank": "subfamily", "name": "Subfamily Uncertain", "genera_count": 3, "range": "L.Sil.-M.Dev."},
                ]
            },
            {"rank": "family", "name": "Eoacidaspididae", "author": "WHITTINGTON", "year": 1959, "genera_count": 3, "range": "Up.M.Cam.-U.Cam."},
        ]
    }

    # =========================================================================
    # ORDER UNCERTAIN
    # =========================================================================
    order_uncertain = {
        "rank": "order",
        "name": "Order Uncertain",
        "genera_count": 8,
        "children": [
            {"rank": "family", "name": "Missisquoiidae", "author": "HUPE", "year": 1955, "genera_count": 1, "range": "L.Ord."},
            {"rank": "family", "name": "Isocolidae", "author": "HOWELL", "year": 1935, "genera_count": 4, "range": "?L.Ord., M.Ord.-U.Ord."},
            {"rank": "family", "name": "Myindidae", "author": "WHITTINGTON", "year": 1959, "genera_count": 1, "range": "M.Ord."},
            {"rank": "family", "name": "Granulariidae", "author": "RAYMOND", "year": 1925, "genera_count": 1, "range": "Up.L.Cam."},
            {"rank": "family", "name": "Sarkiidae", "author": "HUPE", "year": 1955, "genera_count": 1, "range": "M.Ord."},
        ]
    }

    # =========================================================================
    # ORDER AND FAMILY UNCERTAIN (genera not placed in families)
    # =========================================================================
    uncertain_genera = {
        "rank": "note",
        "name": "Order and Family Uncertain",
        "note": "genera (121)",
        "children": [
            {"rank": "note", "name": "Lower Cambrian genera", "genera_count": 14, "range": "L.Cam."},
            {"rank": "note", "name": "Middle Cambrian genera", "genera_count": 26, "range": "M.Cam."},
            {"rank": "note", "name": "Upper Cambrian genera", "genera_count": 41, "range": "U.Cam."},
            {"rank": "note", "name": "Ordovician genera", "genera_count": 38, "range": "Ord.-U.Ord."},
            {"rank": "note", "name": "Devonian genera", "genera_count": 2, "range": "Dev."},
            {"rank": "note", "name": "Unrecognizable genera", "genera_count": 60},
            {"rank": "note", "name": "Nomina nuda", "genera_count": 3},
            {"rank": "note", "name": "Supposed Trilobita here rejected from class", "genera_count": 2},
        ]
    }

    trilobita["children"] = [
        agnostida,
        redlichiida,
        corynexochida,
        ptychopariida,
        phacopida,
        lichida,
        odontopleurida,
        order_uncertain,
        uncertain_genera,
    ]

    return taxonomy


def count_taxa(node, stats=None):
    """Count all taxa at each rank in the tree."""
    if stats is None:
        stats = {}
    rank = node.get("rank", "unknown")
    if rank != "note":
        stats[rank] = stats.get(rank, 0) + 1
    for child in node.get("children", []):
        count_taxa(child, stats)
    return stats


if __name__ == "__main__":
    taxonomy = build_taxonomy()

    # Save to JSON
    output_path = "data/treatise_1959_taxonomy.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, indent=2, ensure_ascii=False)

    # Print summary
    stats = count_taxa(taxonomy["taxonomy"])
    print(f"Saved to {output_path}")
    print(f"\nTaxa counts by rank:")
    for rank, count in sorted(stats.items()):
        print(f"  {rank}: {count}")

    # Count total families
    print(f"\nTotal genera recorded in outline: 1,401 genera + 128 subgenera")
