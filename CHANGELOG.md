# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release.
- `from_lv_xml` parses LabVIEW Flatten-To-XML text into native Python values.
- `to_lv_xml` renders Python values back to XML that Unflatten From XML accepts, driven by
  an `Array`/`Cluster`/scalar-tag schema.
- Covered subset: the `DBL`, `SGL`, `I8`/`I16`/`I32`/`I64`, `U8`/`U16`/`U32`/`U64` numerics,
  `Boolean`, `String`, one-dimensional `Array` and `Cluster`, nested freely, with the
  `<LVData>` file wrapper unwrapped on read. Unsupported types raise `LVXMLError`.
