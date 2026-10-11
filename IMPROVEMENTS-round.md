# Improvements, this round

Ranked by how much each one changes what a user can trust or do. Every type and element
named here traces to `LVXMLSchema.xsd` as shipped in `vi.lib\Utility` of LabVIEW 2026, or
to a file LabVIEW itself wrote.

1. **Ground truth in the test suite.** Ship the official `LVXMLSchema.xsd` and a file
   written by LabVIEW 2026 (the "Flatten and Unflatten XML" example) as fixtures. A
   contract test validates the real file and every schema-derived fixture against the XSD
   and checks that the codec agrees with the XSD on what is valid.
2. **Lossless typed tree.** `parse()` returns a `Document` of frozen `Node` objects that
   keeps every name, raw `<Val>` text, enum choice, `Dimsize` and `NumElts`, and
   `dump()` writes it back in LabVIEW's own layout. A LabVIEW-written file round-trips
   byte for byte; nothing is guessed or reformatted.
3. **Full XSD type coverage.** Every element the schema defines is read: the integer and
   float numerics including `EXT`, the complex `CSG`/`CDB`/`CXT`, `Boolean`, `String`,
   `Path`, `DAQChannel`, the `EB`/`EW`/`EL` enums with their `Choice` list, `Refnum` with
   its optional kind and type fields, multi-dimensional `Array`, `Cluster`, `LvVariant`,
   `Timestamp`, `WDT`, `DynamicData`, `DigitalData` and every waveform element.
4. **Multi-dimensional arrays.** Repeated `<Dimsize>` elements become nested lists in
   row-major order, and `Array(element, ndim=2)` writes them back, rejecting ragged input.
5. **Honest errors.** Every error names its location (`LVData/Cluster[pt]/DBL[x]`). The
   reader rejects what the schema forbids (unknown or misplaced elements, stray text,
   a missing `<Name>`), a `NumElts` or `Dimsize` that disagrees with the elements present,
   a comma decimal separator, out-of-range integers or enum indexes, and duplicate cluster
   field names that a dict would silently merge.
6. **`validate()`.** Collects every problem in a document instead of stopping at the first
   value, for use in tooling and the CLI.
7. **CLI.** `lvxml to-json`, `lvxml to-xml` and `lvxml validate`, with `--version`,
   runnable `--help` examples, errors on stderr and exit status 1.
8. **Escaping and line endings.** Only `&`, `<` and `>` are escaped, as LabVIEW does.
   Carriage returns inside string values survive a read, where a plain XML parser would
   fold them into line feeds.
9. **Real end-to-end test.** Installs the package in editable mode and drives the
   installed `lvxml` console script on the real file, with no mocks.

Deferred: fixed-point `FXP` and the `<Default>`/`<Attributes>` children of a variant are
written by recent LabVIEW versions but are absent from the shipped schema, so they raise
a clear error until a real sample is available to test against.
