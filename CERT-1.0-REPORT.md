# lvxml 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.2.1, a6b93de)
- [x] Baseline gates run on 0.2.1
- [x] Real LabVIEW 2026 ground truth: Flatten To XML files and Unflatten From XML readings (item 7)
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.1 (items 8, 10, 13, 14)
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer (item 16)
- [ ] Gates (item 15)
- [ ] PR open and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Baseline on 0.2.1 (before any change)

Fresh clone of `main` at a6b93de on Elena's PC, Python 3.14:

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .` | exit 0 |
| `mypy --strict src` | exit 0 |
| `mypy --strict src tests` | exit 1 (no type information for `lxml`) |
| `pytest` | passed, the XSD tests skipped (the schema is not on that PC) |
| `pytest --doctest-modules src` | no doctests at all |

## Ground truth (item 7)

LabVIEW 2026 Community 26.3.1f1 is installed on this PC and on 2026-10-16 it could be driven
through its ActiveX VI Server. `scripts/capture-labview-xml.ps1` runs shipped VIs unmodified
(each hashed before and after) and restores every file it touches:

- **Files LabVIEW wrote** (`tests/fixtures/labview2026/save-*.xml`): the project-template VIs
  "Save Settings to XML" and "Save Configuration Settings to XML" flatten a typedef cluster
  (String, `EW` enum, Path, TDMS `Refnum`, Boolean, nested clusters) to an `<LVData>` file.
  Seven runs with values chosen in `scripts/make_labview_jobs.py` (labelled hand-chosen):
  escapes, quotes, tab, CR, LF, `]]>`, spaces, UNC and relative paths, non-ASCII text and
  control characters.
- **Values LabVIEW read** (`load-*.json` from `inputs/*.xml`): "Load Configuration Settings
  from XML" (Boolean, enums, strings, nested clusters) and the shipped example "Read from XML
  File and Unflatten Data" (DBL) read 34 hand-written or `lvxml`-written inputs; the indicator
  values were read back over ActiveX.
- The 0.2.1 fixture `tests/fixtures/real/example-flattened-xml-file.xml` (shipped example
  "Flatten Data and Write to XML File") and NI's `LVXMLSchema.xsd` from the install (local
  only, manifest tracked) are kept.

What LabVIEW 2026 showed, and the 0.2.1 defects it exposed:

| Fact | 0.2.1 |
| --- | --- |
| A `Refnum` is written `Name`, `RefKind`, `Val`: against LabVIEW's own XSD | refused every LabVIEW file holding a refnum |
| Only `&`, `<`, `>` are escaped; reading decodes only those three entities; `&quot;`, `&#65;`, a lone `&` stay literal | decoded them, or raised for a lone `&` |
| Control characters are written raw | refused to read or write them |
| Files are written in the system code page (cp1252) with no encoding declared | bytes input raised a bare decode error |
| Boolean is read as unsigned digits: `2` and ` 1 ` true; `true`, `TRUE`, `-1` refused | read `true`, refused `2` |
| Floats: `nan`, `+Inf`, `INF`, `1e400`, ` 2.5 `, `.5`, `+1`, `5e-324` read; `Infinity`, `+NaN`, `-NaN`, `1,5`, empty refused | read `Infinity` |
| A file without `<Version>` is refused by the file reader; the namespace may be LabVIEW's, the XSD's or none; indentation is fine; a wrong `NumElts` and a negative enum index are refused; an index past the choices is clamped | documented in the guide |
| A file `lvxml` dumped with a `Version` header was read with every value intact | confirms the writer |

Not reachable with shipped VIs: integers other than enum indexes, `SGL`/`EXT`, complex,
multi-dimensional arrays, variants, timestamps and waveforms, and the bare form of Unflatten
From XML on a string. Those rest on the XSD and on the run-time library's format strings, as
the guide states.

## API review (items 1 to 5)

The fifteen public names of 0.2.1 keep their names, parameters and defaults. Behaviour
changes, all in CHANGELOG 1.0.0 and the guide's upgrade list: the LabVIEW text rules above;
schema objects, `Node` and `Document` check their fields when built; `dump` checks `newline`
and `indent`; any bytes-like input is read; messages quote at most 40 characters and
`str()` of an error stays a few hundred characters; errors pickle with message and path;
`LVXMLError`, `Node` and `Document` report module `lvxml`; the command line exits 2 for usage
mistakes, reads `to-xml` JSON as UTF-8, bounds its lines and ends quietly on a closed pipe.
Every public name has a runnable `>>>` example; `tests/test_docs.py` runs every module's
doctests, the README and GUIDE `pycon` blocks and the guide's command transcripts.
`mypy --strict src tests` is clean.

## Author mutation round (item 18)

36 mutations, each applied alone to a fresh clone at ae8887b on Elena's PC (Python 3.14), the
suite run with `-x`, the wheel end-to-end module excluded (the command line is covered in
process). 31 killed at once; P02, E03, K01, L02 and L03 survived and were killed by the
contracts in `tests/test_contract_author.py` (re-applied at 54a9e59, all killed).

| Id | Mutation | Caught by |
| --- | --- | --- |
| A01 | `&quot;` decoded | `test_docs.py::test_module_doctests_pass[lvxml._parse]` |
| A02 | NUL not hidden from the parser | `test_promises.py::test_text_is_read_as_labview_reads_it` |
| A03 | private-use offset shifted | `test_fuzz.py::test_random_values_round_trip_through_text[0]` |
| A04 | carriage returns folded | `test_fuzz.py::test_random_values_round_trip_through_text[0]` |
| A05 | DOCTYPE accepted | `test_types.py::test_doctype_is_refused` |
| A06 | code page hint dropped | `test_docs.py::test_guide_examples_run_and_print_what_they_show` |
| N01 | Boolean reads signs | `test_labview2026.py::...[load-single-bool-minus]` |
| N02 | Boolean `2` false | `test_docs.py::test_module_doctests_pass[lvxml._numbers]` |
| N03 | `Infinity` accepted | `test_labview2026.py::test_lvxml_reads_doubles_as_labview_does[load-dbl-nonfinite-lower]` |
| N04 | comma accepted | `test_promises.py::test_floats_labview_refuses_are_refused[1,5]` |
| N05 | integer range off by one | `test_cli.py::test_validate_reports_ok_and_problems` |
| N06 | complex parts swapped | `test_cli.py::test_to_json_values_writes_complex_as_re_im` |
| N07 | `SGL` overflow unchecked | `test_types.py::test_encoding_errors_are_honest[1e+39-SGL-single]` |
| P01 | `RefKind` before `Val` refused | `test_docs.py::test_guide_examples_run_and_print_what_they_show` |
| P02 | depth limit one level late | after a new contract: `test_contract_author.py::test_nesting_is_allowed_up_to_max_depth_and_refused_one_deeper` |
| P03 | `Dimsize` order reversed | `test_fuzz.py::test_mutated_files_only_raise_lvxml_error[0]` |
| P04 | mixed namespaces accepted | `test_hardening.py::test_children_must_share_the_root_namespace` |
| D01 | `RefKind` written after `Val` | `test_docs.py::test_guide_examples_run_and_print_what_they_show` |
| D02 | quotes escaped in text | `test_fuzz.py::test_mutated_files_only_raise_lvxml_error[0]` |
| D03 | `newline` unchecked | `test_promises.py::test_dump_checks_its_arguments` |
| D04 | surrogate U+D800 written | `test_hardening.py::test_unwritable_text_is_an_lvxml_error` |
| E01 | empty array without its default element | `test_docs.py::test_guide_examples_run_and_print_what_they_show` |
| E02 | enum index bound off by one | `test_types.py::test_encoding_errors_are_honest[2-schema3-outside]` |
| E03 | `bool` accepted for integer tags | after a new contract: `test_contract_author.py::test_a_bool_is_not_a_number` |
| C01 | enum index past the choices accepted | `test_labview2026.py::...[load-single-enum-past]` |
| C02 | `NumElts` unchecked | `test_docs.py::test_guide_examples_run_and_print_what_they_show` |
| K01 | error bound lifted | after a new contract: `test_contract_author.py::test_an_error_built_from_huge_text_stays_short` |
| K02 | pickle loses the path | `test_promises.py::test_errors_are_bounded_located_and_pickle` |
| T01 | quote limit lifted | `test_docs.py::test_module_doctests_pass[lvxml._text]` |
| F01 | `Node.val` type unchecked | `test_promises.py::test_nodes_and_documents_check_their_field_types` |
| F02 | lists kept as lists | `test_promises.py::test_nodes_and_documents_check_their_field_types` |
| S01 | unknown scalar tag accepted | `test_docs.py::test_guide_examples_run_and_print_what_they_show` |
| S02 | `Cluster` fields not copied | `test_promises.py::test_schema_objects_check_themselves` |
| L01 | usage mistake exits 1 | `test_cli.py::test_problems_exit_1_and_usage_mistakes_exit_2_on_stderr` |
| L02 | command line bound lifted | after a new contract: `test_contract_author.py::test_every_command_line_is_bounded` |
| L03 | `to-xml` reads JSON with `--encoding` | after a new contract: `test_contract_author.py::test_to_xml_reads_its_json_as_utf8_whatever_the_xml_encoding` |

## Packaging, interpreters and upgrade (items 8, 10, 11, 13, 14)

On this PC at b5e37da, from a fresh clone: `python -m build`, `twine check --strict` PASSED
for both archives, `check-wheel-contents` OK. Wheel: the package, `py.typed`, LICENSE and
metadata only. Sdist: source, tests with their fixtures (LabVIEW captures and inputs, the
NI manifest without the schema), the capture scripts and the docs. The sdist suite with
`src` removed, run against the installed wheel (the wheel end-to-end tests included):

| Python | Result |
| --- | --- |
| 3.10.19 | 360 passed, 40 skipped |
| 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2 free-threaded | 361 passed, 39 skipped each |

Skips: the XSD checks (NI's schema is not shipped) and one metadata test that needs
`tomllib` on 3.10. No interpreter from 3.10 up on this PC was left out.

Upgrade: `pip install lvxml==0.2.1` from PyPI into a fresh venv, a 30-call battery, the 1.0.0
wheel installed over it with `--upgrade`, the battery again: 10 results identical, 20
different, each one a change in the list above (version, entities, lone `&`, control
characters, Boolean `true` and `2`, `Infinity`, refnum order read and written, code page
hint, `memoryview`, schema, node and `dump` checks, raw control characters written, bounded
message, error module).
