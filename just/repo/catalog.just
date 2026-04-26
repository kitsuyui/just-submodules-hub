repo_catalog_source_dir := source_directory()

mod duplicates "catalog/duplicates.just"
mod languages "catalog/languages.just"

# Deprecated compatibility aliases. Prefer the canonical namespace/resource/verb commands.
alias python := languages::python::list
alias js := languages::js::list
alias go := languages::go::list
alias rust := languages::rust::list
alias duplicate-filenames := duplicates::filenames::list
