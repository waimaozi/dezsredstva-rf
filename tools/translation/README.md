# Demand-led translations

The publisher uses real Wordstat phrase results (Russia, last 30 days). Google
suggestions are a fallback and carry no invented search counts. Rare phrases
have no volume floor. Catalog order prioritizes a specific answer over volume.

`catalog.json` is an editorially mapped source library. The initial three topics
cover ATP interpretation, solution preparation and reusable cleaning equipment.
Every run refreshes nine seed searches and records unmatched queries in
`queue.json`. This is a bounded library: it does not pretend to find and license
new sources automatically. Exhausting it produces `needs_sources` and a failed
health check. Extend it by checking a source's rights, question fit, complete
section boundaries and context, then pinning its extracted SHA-256. A change to
an approved section holds publication until it is checked again.
If CDC is unreachable, an approved local snapshot no older than 30 days may be
used. Its retrieval mode and original check date are recorded. After 30 days,
failure to fetch the source holds publication. The snapshot hash is rechecked.

Content is a complete translation of the named section, with tables, immutable
source links, original date, context and AI disclosure. English and Russian
copies are downloadable standalone HTML. The model cannot write the headline,
scope, context or markup. Coverage and literal numbers are checked in code;
a separate model call checks meaning. These checks are not specialist review.
No abstract expansion, fabricated expert, invented personal experience or
Russian regulation is generated. Existing historical digests are preserved.

## Operation

Use an isolated, clean checkout of main at
`/home/openclaw/dezsredstva-translations`. Install Python requirements and run
`npm ci`. The service runs as `openclaw`; its weekly UTC timer is Tuesday 06:00
(09:00 Moscow), with a non-overlapping lock and a 25-minute timeout.

The private runtime env file contains paths to `KIE_API_KEY_FILE` and
`YANDEX_API_KEY_FILE`, plus `DEZSREDSTVA_STATE` and `GIT_SSH_COMMAND` for a
repository-scoped deploy key. Keep it and keys mode 600 outside the checkout.
Never put credentials into command arguments, Git URLs or evidence.

Preview with `python3 tools/publish-translations.py --state-dir /private/state`.
This makes billable calls and writes evidence, but cannot write article files,
publication state or commits. Production entrypoint: `bash tools/run-daily.sh`.
It fetches main, refuses a dirty/diverged checkout, produces at most one article,
builds before committing, pushes, verifies the actual live page and then submits
IndexNow. Failed pushes retain the commit; failed builds retain files for repair.
Never reset or blindly stash the operational checkout to recover.

Private `last-run.json` and per-run files record source, search response, model
usage, translation, review, build log and failure reason. Inspect with
`systemctl status dezsredstva-publisher.service` and
`journalctl -u dezsredstva-publisher.service`. The public heartbeat is
`/publisher-status.json`; the daily GitHub Actions health workflow fails on a
stale heartbeat (9 days), an empty/held source queue or a missing live article.
It detects missed weekly output; private service logs identify the cause.

Before changing a model or extraction format, run the unit tests and a live
positive/negative fidelity probe. Recheck rendering and the offline download.
Downloads send the existing Metrika counter the `translation_download` event.
Search impressions, downloads and repeat visits still need time to accumulate;
publication is not evidence that readership has grown.
