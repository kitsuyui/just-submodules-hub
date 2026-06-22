# Contributing

Thank you for your interest in contributing to just-submodules-hub!

## Getting Started

1. Fork the repository and clone your fork.
2. Install the required tools:
   ```sh
   brew install just git uv
   ```
3. Run the test suite to verify your setup:
   ```sh
   just test
   ```

## Making Changes

- Open an issue to discuss significant changes before starting work.
- Keep pull requests focused on a single concern.
- Follow the existing code style (enforced by `ruff`).
- Add or update tests for any new or changed behavior.
- Run `just lint` and `just test` locally before submitting.

## Pull Request Process

1. Create a branch from `main` with a descriptive name (e.g. `fix/issue-description`).
2. Write a clear PR title and description explaining the motivation and scope of the change.
3. Ensure all CI checks pass.
4. A maintainer will review and merge your PR.

## Reporting Bugs

Please open a [GitHub Issue](https://github.com/kitsuyui/just-submodules-hub/issues/new/choose) with:
- A clear description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, tool versions)

## Security Vulnerabilities

See [SECURITY.md](SECURITY.md) for how to report security issues privately.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
