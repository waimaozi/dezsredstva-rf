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

The first release established the source-to-publication workflow. The approved
research queue below now connects reviewed packages to the weekly timer.

## Approved research queue (29 October 2026)

The production weekly entrypoint now runs `tools/publish-research.py`, replacing
scheduled generation from the exhausted CDC catalog. It does not discover,
license or translate papers unattended. `candidates.json` lists verified sources
whose translation/review is still required; these cannot be published by the job.

An approved package lives in `packages/<translationId>/`: `files/` holds the
article and its own local downloads; `evidence/` preserves the full source,
translation, source check and explicit editorial review. `manifest.json` binds
all files/evidence to SHA-256 hashes, source identifiers, a checked CC BY licence,
reviewer, scope and an earliest release date. Unsupported licences require a
separate reviewed implementation, not an override. Set `status` to `approved`
only after completing source, meaning, figure/table, PDF and rendering checks.
A source candidate or a model PASS alone is not approval.

`python3 tools/publish-research.py --state-dir /private/preview` validates without
publishing or making model calls. The timer uses `bash tools/run-daily.sh`, which
locks, fetches/fast-forwards main, retries a retained push and releases at most
one translation per ISO week. Failed builds remove only this attempt's newly
created, unchanged files. Existing differing content, a partial installation,
changed evidence, a dirty/diverged checkout or changed download bytes stops the
release for inspection; never reset/stash away unexplained files.

`last-publication.json` retains the deployment-verification job across failed
pushes/deployments. The verifier checks title, source DOI, every download hash
and the translations hub before IndexNow. Public `awaiting_deployment` is the
commit-time status; private `live_verified` records the later check. The daily
health workflow independently checks the live article/downloads. An empty queue
returns `needs_translation` (successful runtime, editorial attention still
required); the health workflow flags missed output. Two verified sources do not
mean two scheduled translations. To retire a consumed package after subsequent
editorial corrections, archive its manifest status after live verification;
keep its evidence, and never mutate its approved payload in place.
