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
- [x] Five QA lenses report PASS (item 19): a round 3, b round 2, c round 2, d round 2, e round 6
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
  File and Unflatten Data" (DBL) read 31 hand-written or `lvxml`-written inputs; the indicator
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

On this PC at f7cbb81 (the final code), from a fresh clone: `python -m build`,
`twine check --strict` PASSED for both archives, `check-wheel-contents` OK. Wheel: the
package, `py.typed`, LICENSE and metadata only. Sdist: source, tests with their fixtures
(LabVIEW captures and inputs, the NI manifest without the schema), the capture scripts and the
docs. The sdist suite with `src` removed, run against the installed wheel (the wheel
end-to-end tests included):

| Python | Result |
| --- | --- |
| 3.10.19 | 532 passed, 41 skipped |
| 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2 free-threaded | 533 passed, 40 skipped each |

Skips: the XSD checks (NI's schema is not shipped; with it restored by
`scripts/capture_ni.py` they run and pass, lens d round 2) and one metadata test that needs
`tomllib` on 3.10. No interpreter from 3.10 up on this PC was left out.

Upgrade: `pip install lvxml==0.2.1` from PyPI into a fresh venv, a 30-call battery, the 1.0.0
wheel (f7cbb81) installed over it with `--upgrade`, the battery again: 9 results identical, 21
different, each one a documented change (version, the two new names, entities, lone `&`,
control characters, Boolean `true` and `2`, `Infinity`, refnum order read and written, code
page hint, `memoryview`, schema, node and `dump` checks, raw control characters written,
bounded message, error module). Lens d compared 221 behaviours the same way at 44836e2: 93
differences, all documented.

## Independent QA lenses (item 19)

Each lens was a fresh agent that read the factory rules and CERT-1.0.md, ran everything in
its own clone and venvs (heavy runs on Elena's PC, the laptop or this PC through the turn
system) and reported only to the orchestrator. Later rounds confirmed the earlier findings
and swept at most 40 new mutations on the code changed since.

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a. API and docs | 1 | 7836e92 | FAIL (1 medium, 5 low) | README (10), GUIDE (26) and every docstring example run on the wheel; about 150 calls compared with PyPI 0.2.1; strict mypy consumer. Medium: a Windows reader closing the pipe (EINVAL) printed an error. Low: changelog missing items the guide lists; guide overstated what `dump` checks; `to_value("x")` raised `AttributeError`; refnum wording; schema classes reported `lvxml._schema`, `Schema`/`Value` not exported. Fixed in 04c9db7 (EINVAL treated as a closed pipe, `TypeError` from `to_value`, `lvxml.Schema` and `lvxml.Value` public, docs corrected, `tests/test_contract_lenses.py`) |
| a. API and docs | 2 | 04c9db7 | FAIL (1 low) | all six round-1 findings confirmed fixed; new wording said "a tree" where `to_value` takes only a `Node`. Fixed in cd2df12 |
| a. API and docs | 3 | cd2df12 | PASS | wording confirmed against behaviour and against 0.2.1 |
| b. Correctness and ground truth | 1 | cd2df12 | FAIL (3 medium, 3 low) | 103 LabVIEW 2026 runs with its own values and inputs; 8 committed jobs re-run byte-identical; 1362 structural mutants checked against the XSD with lxml. Medium: any white space trimmed (LabVIEW takes spaces only); a plus sign on enum indexes; refnum kinds after `<Val>` and decimal refnum values accepted although LabVIEW refuses them. Low: `<Version>` after a value; SI suffixes and other lenient LabVIEW readings undocumented; declared encodings ignored by LabVIEW. Fixed in 0a9bab6 (spaces only, no plus sign on integers, refnum order and `0x` value, `<Version>` first, `validate` reports a missing header, guide updated) |
| b. Correctness and ground truth | 2 | 0a9bab6 | PASS | 94 earlier LabVIEW jobs and 9 probes re-compared; every remaining difference documented (lvxml stricter, never a different value) |
| c. Adversarial and robustness | 1 | 0a9bab6 | FAIL (3 high, 2 medium, 3 low) | 168,807 fuzz calls, 408 CLI runs by subprocess, 33 scaling series. High: quadratic float and complex regexes; Python's integer digit limit escaping as `ValueError` and CLI tracebacks; non-text codecs (`base64`) crashing the CLI. Medium: `UnicodeEncodeError`, `UnicodeError` and `RecursionError` escaping the readers; control characters and line breaks from the input written raw to stderr. Low: unbounded `validate` strings; namespace corrupted by the private-use escape; mixed key types in `from_dict`. Fixed in 44836e2 (`tests/test_contract_hostile.py`) |
| c. Adversarial and robustness | 2 | 44836e2 | PASS | 274,346 fuzz calls, 408 CLI runs, 33 series: no unexpected exception, all linear or constant |
| d. Packaging and real e2e | 1 | 44836e2 | FAIL (1 medium) | sdist and wheel built, `twine check --strict`, contents inspected, suite from the sdist against the wheel on 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t (443 passed each with the schema, 3.10 skipping one `tomllib` test), PyPI 0.2.1 upgraded in place with 221 behaviours compared (93 differences, all documented). Medium: `tests/fixtures/ni/MANIFEST.json` was not valid JSON, so `scripts/capture_ni.py` could not restore the schema. Fixed in c82c89d (`tests/test_sources_manifest.py`) |
| d. Packaging and real e2e | 2 | c82c89d | PASS | capture script restores the schema; 446 passed with 0 skipped; archives changed only by the new test |
| e. Contract strength | 1 (blind) | c82c89d | FAIL | 118 mutations designed from the source: 69 killed, 3 equivalent, 46 survivors; one bug (a quote in the namespace did not round-trip). Its 46 contracts added as `tests/test_contract_strength.py` and `tests/test_contract_strength_two.py`; entities in attribute values fixed (89a71e5) |
| e. Contract strength | 2 (new agent, the first hit a usage limit) | 7110f36 | FAIL | the 46 re-applied mutants all killed; 32 new on the ampersand change: 18 killed, 6 equivalent, 8 survivors, one BOM case not equivalent, and a tag ending at a `>` inside quotes. Fixed in 72c967a (`tests/test_contract_entities.py`) |
| e. Contract strength | 3 | 72c967a | FAIL | 30 new mutations: 9 survivors; the quote-aware tag regex split comments holding `<`. Fixed in 94d0456 |
| e. Contract strength | 4 | 94d0456 | FAIL | 32 new: 14 survivors; the unclosed-comment check refused an opener inside other markup. Replaced by one ordered linear markup scanner in 9af4ca4 (`tests/test_contract_markup.py`, `tests/test_contract_markup_two.py`) |
| e. Contract strength | 5 | 9af4ca4 | FAIL | 30 new on the scanner: 22 killed, 2 equivalent, 6 survivors; no defect; `load()` linear on 26 hostile shapes. Contracts added in c6f79c7 |
| e. Contract strength | 6 | c6f79c7 | PASS | the six survivors killed; every mutant of rounds 1 to 5 killed or argued equivalent |

## Independent reviewer (item 16)

| Review | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- |
| 1 | 3d84972 | FAIL (1 medium, 3 low) | the four gates each alone on a fresh clone on Elena's PC (520 passed, 40 skipped); items 1 to 5, 7 to 15 and 19 PASS; house rules PASS. Its own 40 mutations on the code changed on the branch: 30 killed, 2 equivalent (`_empty_rows` is only reached when a size is 0; every text codec that encodes "x" decodes it back), 8 survivors (private-use character U+E000 not hidden, BOM before the declaration, white space in counts, complex separator, empty shape past the count limit, tab indent, CLI cut marker, cluster keys of mixed types). Low: input count in this report (31, not 34), stale interpreter counts, `LVXMLError.path` kept whole. Contracts added in `tests/test_contract_review.py` (f7cbb81); report refreshed |
