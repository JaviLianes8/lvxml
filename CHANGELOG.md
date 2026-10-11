# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Added

- Every element of LabVIEW's `LVXMLSchema.xsd`: `EXT`, complex `CSG`/`CDB`/`CXT`, `Path`,
  `DAQChannel`, the `EB`/`EW`/`EL` enums, `Refnum`, `LvVariant`, `Timestamp`, `WDT`,
  `DynamicData`, `DigitalData` and every waveform element.
- Multi-dimensional arrays: nested lists in row-major order, `Array(element, ndim=2)`.
- `LVEnum(choices, tag)` schema; enum values encode from a label or an index.
- Lossless typed tree: `parse`, `dump`, `Node`, `Document`, `to_node`, `to_value`, and
  dict conversion with `to_dict`/`from_dict`. LabVIEW-written files round-trip byte for
  byte.
- `from_lv_xml_all` for files holding several values.
- `validate`, which lists every problem with its location.
- `lvxml` command with `to-json`, `to-xml` and `validate`, also as `python -m lvxml`.
- `LVXMLError.path` locating the offending element.
- Tests against the official XSD and a file written by LabVIEW 2026.

### Changed

- The reader enforces the schema's element order and rejects unknown elements, stray
  text, attributes, a missing `<Name>`, elements outside the root's namespace, a DOCTYPE
  and CDATA sections. Nesting deeper than 100 levels raises.
- `NumElts` must match the elements present, a `Cluster`'s `NumElts` is no longer
  ignored, and an integer outside its type's range or duplicate cluster field names now
  raise instead of being read silently. A comma decimal separator still raises, now with
  a hint.
- Bytes input is decoded by the encoding its XML declaration names (UTF-8 by default);
  any other input type raises `TypeError`.
- Error messages start with the location of the offending element.
- Floats are read strictly: digits with an optional period and exponent, or `NaN`,
  `Inf` and `Infinity` in any case. Python-only spellings such as `1_000` raise.
- `to_lv_xml` writes empty elements as `<Name></Name>`, like LabVIEW, and non-finite
  floats as `NaN`, `Inf` and `-Inf`. A `SGL` or `CSG` value too large for single
  precision raises. An `Array` element can no longer be an `Array`, which the schema
  does not allow.

## [0.1.0]

- First release.
- `from_lv_xml` parses LabVIEW Flatten-To-XML text into native Python values.
- `to_lv_xml` renders Python values back to XML that Unflatten From XML accepts, driven by
  an `Array`/`Cluster`/scalar-tag schema.
- Covered subset: the `DBL`, `SGL`, `I8`/`I16`/`I32`/`I64`, `U8`/`U16`/`U32`/`U64` numerics,
  `Boolean`, `String`, one-dimensional `Array` and `Cluster`, nested freely, with the
  `<LVData>` file wrapper unwrapped on read. Unsupported types raise `LVXMLError`.
