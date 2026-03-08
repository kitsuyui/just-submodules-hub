# `repo catalog`

Use `repo catalog` to classify or inspect the managed repositories that already exist in the hub.

## Commands

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
