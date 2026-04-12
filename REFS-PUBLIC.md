# REFS-PUBLIC.md - Public References

> Record external public repositories, datasets, documentation, APIs, or other
> public resources that this repository utilizes or depends on.
> This file is tracked and intentionally kept free of private or local-only details.

## Public Repositories

- No fixed external code repository is the main upstream; this repo packages local reusable test helpers.

## Public Datasets and APIs

- No standing public datasets or APIs are required; the repo provides local fixtures, mocks, and test scaffolding.

## Documentation and Specifications

- https://docs.pytest.org/ - pytest fixture and marker integration reference
- https://docs.python.org/3/library/unittest.html - unittest base-class and assertion model used by DynoTestCase

## Notes

- Consumer repos bring their own application APIs and datasets. dyno-lab only owns the reusable test bench surface.
