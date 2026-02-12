# ICS International Chronostratigraphic Chart (GTS 2020)

## Source

- **Title:** International Chronostratigraphic Chart
- **Version:** GTS 2020 (v2020/03)
- **Publisher:** International Commission on Stratigraphy (ICS)
- **Format:** SKOS/RDF (Turtle)
- **URL:** https://stratigraphy.org/chart
- **Data file:** https://vocabs.ardc.edu.au/repository/api/lda/csiro/international-chronostratigraphic-chart/geologic-time-scale-2020/resource.ttl

## License

The ICS chart data is published under **CC-BY 4.0** (Creative Commons Attribution 4.0 International).

## Contents

- `chart.ttl` — Full ICS chronostratigraphic chart in Turtle (SKOS/RDF) format, 179 concepts covering Eons through Ages.

## Usage in Trilobase

Imported into `ics_chronostrat` table by `scripts/import_ics.py`.
Mapped to Trilobase `temporal_ranges` codes via `temporal_ics_mapping` table.
