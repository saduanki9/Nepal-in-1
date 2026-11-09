# .github-workflows-# This workflow uses actions that are not certified by GitHub.
# They are provided by a third-party and are governed by
# separate terms of service, privacy policy, and support
# documentation.

# This workflow lets you generate SLSA provenance file for your project.
# The generation satisfies level 3 for the provenance requirements - see https://slsa.dev/spec/v0.1/requirements
# The project is an initiative of the OpenSSF (openssf.org) and is developed at
# https://github.com/slsa-framework/slsa-github-generator.
# The provenance file can be verified using https://github.com/slsa-framework/slsa-verifier.
# For more information about SLSA and how it improves the supply-chain, visit slsa.dev.

name: SLSA generic generator

on:
  workflow_dispatch:
  release:
    types: [created]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      digests: ${{ steps.hash.outputs.hashes }}

    steps:
      - uses: actions/checkout@v4

      - name: Prepare project artifacts
        shell: bash
        run: |
          set -euo pipefail

          echo "Repository contents:"
          find . -maxdepth 3 -type d | sort

          if [ ! -d artifacts ]; then
            echo "artifacts directory not found"
            exit 1
          fi

          echo "Artifact files:"
          find artifacts -type f | sort

      - name: Generate subject for provenance
        id: hash
        shell: bash
        run: |
          set -euo pipefail

          if [ ! -d artifacts ]; then
            echo "artifacts directory not found"
            exit 1
          fi

          files=()
          while IFS= read -r -d '' file; do
            files+=("$file")
          done < <(find artifacts -type f -print0)

          if [ "${#files[@]}" -eq 0 ]; then
            echo "No files found in artifacts/"
            exit 1
          fi

          echo "hashes=$(sha256sum "${files[@]}" | base64 -w0)" >> "$GITHUB_OUTPUT"

  provenance:
    needs: [build]
    permissions:
      actions: read
      id-token: write
      contents: write
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v1.4.0
    with:
      base64-subjects: "${{ needs.build.outputs.digests }}"
      upload-assets: true
