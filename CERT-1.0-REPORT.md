# lvxml 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.2.1, a6b93de)
- [x] Baseline gates run on 0.2.1
- [x] Real LabVIEW 2026 ground truth: Flatten To XML files and Unflatten From XML readings (item 7)
- [ ] API review and 1.0.0 API changes (item 1)
- [ ] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.2.1 (items 8, 10, 13, 14)
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
