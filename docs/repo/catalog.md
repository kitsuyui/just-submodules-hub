# `repo catalog`

Use `repo catalog` to classify or inspect the managed repositories that already exist in the hub.

## Intent

Use these commands when you want a quick local catalog of managed repositories by language marker or filename pattern.

## Examples

```sh
just repo catalog python
just repo catalog js
just repo catalog go
just repo catalog rust
just repo catalog duplicate-filenames
```

## Purpose

- detect repositories by common project markers
- inspect duplicated tracked filenames across managed repositories
- keep lightweight discovery local to the hub checkout
