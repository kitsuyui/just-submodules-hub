# `repo::catalog`

Use `repo::catalog` to classify or inspect the managed repositories that already exist in the hub.

## Intent

Use these commands when you want a quick local catalog of managed repositories by language marker or filename pattern.

## Examples

```sh
just repo::catalog::languages::python::list
just repo::catalog::languages::python::every '<command>'
just repo::catalog::languages::js::list
just repo::catalog::languages::js::every '<command>'
just repo::catalog::languages::go::list
just repo::catalog::languages::go::every '<command>'
just repo::catalog::languages::rust::list
just repo::catalog::languages::rust::every '<command>'
just repo::catalog::duplicates::filenames::list
```

`languages::*::every` uses the same batch runner as `repo::submodule::every`, but prefilters the submodule set with the language marker used by `languages::*::list`.

## Deprecated aliases

The previous flat commands remain available as compatibility aliases. Prefer the primary commands above.

| Deprecated alias | Use instead |
| --- | --- |
| `python` | `languages::python::list` |
| `js` | `languages::js::list` |
| `go` | `languages::go::list` |
| `rust` | `languages::rust::list` |
| `duplicate-filenames` | `duplicates::filenames::list` |

## Purpose

- detect repositories by common project markers
- inspect duplicated tracked filenames across managed repositories
- keep lightweight discovery local to the hub checkout
