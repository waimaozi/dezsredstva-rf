# Full scientific translations: bounded publication cycle

The first complete cycle recorded here upgraded the existing microplastics digest
(PMID 42688105) on 17 October 2026. Its original URL and publication date remain;
`updated` records the full-translation release. The article has the full main
text, all five figures with separate Russian reading keys, bibliography,
funding/author disclosures, Russian PDF, offline Russian/English HTML and the
publisher's original PDF. Separate supplementary PDF/XLSX files are outside the
explicitly stated scope.

## Source check

```sh
python3 tools/research/probe.py --pmid 42688105 --out /private/research/42688105
```

This saves the PubMed record, notices, identifiers, full JATS when available,
permissions text and source hash. It distinguishes the paper's identifiers from
those of cited references and checks the downloaded article's PMID, PMCID and
DOI. A withdrawal/retraction or expression of concern returns exit 2 and holds
that source. Missing or mismatched evidence returns exit 1. Full text available
(exit 0) still requires an editorial decision about usefulness, rights and scope.
Do not infer translation permission merely from PMC availability.

## Repeat the proven steps

1. Name the professional reader and a concrete question the paper helps answer.
   Inspect actual abstracts with TypeSafe as advisory triage. Search Wordstat and
   Russian results to understand vocabulary and existing coverage; rare queries
   have no volume floor. Record empty responses as unavailable counts.
2. Run the source check and inspect the publisher's reuse licence. Preserve the
   exact full source and assets; verify identifiers and extraction boundaries.
3. Extract the complete named scope into ordered segments with table structure,
   superscripts/subscripts, inequalities, captions and references preserved.
   Include funding and other author disclosures from front/back matter. Declare
   supplementary files separately; do not expand an abstract into a full article.
4. Translate segments; check coverage and literal numbers/inequalities in code.
   Use a bounded semantic check plus direct review of methods, results, caveats,
   units, and sampled passes. Record corrections and false negatives. The first
   cycle found an unsupported microscopy-method detail despite a model PASS;
   model output does not authorize unattended publication.
5. Keep editorial context and figure-reading keys separate from the translation.
   Preserve graphs; explain source inconsistencies without silently redrawing
   data. Build offline files and inspect the Russian PDF's figures and page flow.
6. Build and check the actual site, validate source attribution and downloads,
   merge the content PR, verify the deployed page/files from Russia, then submit
   the changed URLs to IndexNow. Acceptance is not indexing.

The acquisition command, release manifest and monitoring are reusable. This is
one verified, editorially reviewed publication cycle, not an enabled autonomous
paper-discovery/publication service. The existing weekly CDC-section publisher
keeps its bounded catalog and reports `needs_sources` when exhausted; this new
research article does not disguise that state as an automated weekly success.
