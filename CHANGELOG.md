# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-16

The public API is now stable: the seventeen names in `lvxml.__all__`, their parameters and
defaults, the error types and the command line. Every rule below was checked against what
LabVIEW 2026 writes and reads (see the guide, "What each rule rests on").

### Changed

- Text is read as LabVIEW reads it: only `&lt;`, `&gt;` and `&amp;` are decoded, so
  `&quot;`, `&apos;`, numeric references and a lone `&` are kept as written.
- Control characters are read and written raw, as LabVIEW writes them.
- `Boolean` text is unsigned digits, `0` false and any other number true; `true` and
  `false` raise.
- `Infinity` in any spelling raises, as LabVIEW refuses it.
- A refnum's `RefKind` and `RefType` are read and written before `<Val>`, where LabVIEW 2026
  puts them; after `<Val>`, the shipped XSD's order, which LabVIEW refuses, they raise. A
  refnum value must be `0x` and hex digits.
- Spaces around numbers are allowed and other white space raises; an integer or enum index
  with a plus sign raises.
- Number text longer than 1000 characters, a `Dimsize` or `NumElts` above 2**63 - 1, an
  array with more than 100 dimensions and text with a lone surrogate raise `LVXMLError`, so
  hostile input stays cheap; every check runs in linear time.
- A `<Version>` after a value raises; `validate` reports an `<LVData>` document without one.
- Bytes that are not UTF-8 raise with a hint that LabVIEW writes the system code page;
  `bytearray` and `memoryview` are read; an encoding the declaration names that Python
  lacks raises `LVXMLError` with a short message.
- `Array`, `Cluster` and `LVEnum` check their contents when built (`ValueError` for an
  unknown tag, `TypeError` for a wrong type); a non-integer `ndim` raises `TypeError`;
  `Cluster` copies its fields into a new dict.
- `Node` and `Document` check their field types when built and store lists as tuples.
- `dump` takes only CRLF, LF or CR as `newline` and spaces and tabs as `indent`; `dump`
  raises `TypeError` for anything but a `Document` or `Node`, `to_value` for anything but a
  `Node`.
- Error messages quote at most 40 characters of a value and stay bounded, and some wording
  changed (`unknown scalar tag`, `cannot decode byte N as utf-8`); errors pickle with their
  message and path; every public class reports the module `lvxml`.
- The command line exits with status 2 for usage mistakes, reads `to-xml` JSON as UTF-8,
  bounds its problem lines and escapes control characters in them, refuses an `--encoding`
  that is not a text encoding as a usage mistake, ends quietly on a closed pipe; `main` returns 0
  for `--help` and `--version`.

### Added

- `lvxml.Schema` and `lvxml.Value`, the schema and value types for annotations.
- `GUIDE.md`, with an upgrade list from 0.2.
- Ground truth from LabVIEW 2026: files it wrote and values it read back, with the scripts
  that capture them.
- Tests: executable documentation, the built wheel driven from a throwaway venv, seeded
  fuzzing, and contracts proven by deliberate mutations.

## [0.2.1] - 2026-10-13

### Changed

- NI's `LVXMLSchema.xsd` is no longer tracked or shipped in the sdist. `scripts/capture_ni.py`
  copies it from a local LabVIEW install into `tests/fixtures/ni` (checked against the tracked
  manifest), and the tests that validate against it skip when it is absent.

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
