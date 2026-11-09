# MANTO atlas deployment proposal

Inspected read-only on 9 November 2026. No infrastructure changes performed.

## Verified target and existing capability

- Proposed hostname `manto.symmachus.org`: current DNS NXDOMAIN; no matching vhost
  or directory found. Public origin for the existing sibling convention is
  `59.167.239.92`, with a proxied Cloudflare A record, TTL 1.
- Existing repository: `https://github.com/solresol/pausanias.git`. Public read
  access requires no new Git credential. Atlas source lives under `manto_atlas/`.
- Raksasa: Linux, existing Greg sudo access verified; no `manto` OS account.
- Merah: OpenBSD, `merah.cassia.ifost.org.au`; Greg SSH and doas access verified.
  Use doas, not Linux-specific sudo commands. No `manto` OS account.
- Existing Merah httpd serves Pausanias under
  `/var/www/vhosts/pausanias.symmachus.org/htdocs/`; relayd exposes public HTTP and
  forwards to internal httpd at `192.168.91.1:80`.
- Existing Pausanias HTTPS works through Cloudflare. No origin IPv4 443 listener
  was observed. The actual zone TLS policy is unverified; do not assume strict
  origin TLS or change a zone-wide setting to make this site work.
- Existing reporting destination is
  [#pausanias](https://ifost.slack.com/archives/C0CDAQ68FV2), channel `C0CDAQ68FV2`.
  The existing service-owned webhook file is private; its contents were not read.
- PG18 is on `/var/run/postgresql`, port 5433, database `pausanias`. Manual read
  queries work as Greg. The `manto` DB role does not exist. Greg's superuser
  capability is not an appropriate grant for the new job.

## Exact proposed account and access scope

1. Raksasa unprivileged service account `manto`, home `/home/manto`, public source
   checkout `/home/manto/pausanias`. Do not grant sudo or reuse a personal SSH key.
2. Merah restricted publishing account `manto`, limited to
   `/var/www/vhosts/manto.symmachus.org/`. Proposed served root:
   `/var/www/vhosts/manto.symmachus.org/htdocs/`.
3. A new dedicated Ed25519 private key owned by Raksasa's `manto`, stored only in
   that account's private `.ssh` directory. Install only its public key for
   Merah's `manto`. Reject forwarding, PTY, interactive shell and unrelated file
   access. Merah already has `/usr/local/bin/rrsync`.
4. Prefer a narrow atomic-release receiver: upload into a versioned staging
   directory, verify manifest/checksums, promote only a complete validated build,
   and retain the previous release. Plain forced-command rrsync to htdocs is
   simpler but is not an atomic deployment guarantee. The chosen receiver and
   exact writable paths must be reviewed before key installation.
5. If using live source reads, a peer-authenticated, non-superuser DB role
   `manto`, CONNECT to the existing database, schema USAGE and SELECT only on:
   `manto_releases`, `manto_entity_details`, `manto_edges`, `manto_place_links`,
   `pleiades_places`, `passages`, `translations`,
   `passage_place_state_mentions`, `place_survival_model_runs`.
   No table writes, sequence privileges, role administration, creation rights or
   access to unrelated tables. Default read-only transactions and bounded query
   timeouts. A service-produced export snapshot could avoid a new live DB grant,
   but its access and scheduled export ownership must be designed explicitly.
6. Existing-channel Slack reporting under job ID `manto-research`, through a
   separately approved scoped credential/service. Do not make the existing
   Pausanias webhook world/group-readable or copy secret values into Git.

Generating/installing the key and creating persistent account/database access
require the applicable action-time approval for this exact scope. Existing root
capability and broad project intent do not substitute for that approval.

## Cloudflare still to verify

No Cloudflare administrative connector was found. The conventional
`$HOME/.cloudflare` file is absent for Greg on Raksasa. Other credential-related
configuration exists, but contents, token validity, account/zone and permission
scope have not been verified or transmitted. The existing Word Garden helper
establishes the sibling DNS convention, but some helper flows modify config even
when discovering zones; do not run them as supposedly read-only probes.

Before creating the proposed record, verify the actual `symmachus.org` zone,
existing token permissions and account, DNS conflicts, TLS mode and origin routing
through an authorized route. Do not create broader credentials or weaken TLS.
Any newly required credential/access grant or security-sensitive networking change
must be separately approved with its exact scope.

## Proposed operational behavior

- Initially run an explicit approved build only; do not install a recurring job
  until its input release, data publication scope and deployment path are checked.
- Subsequent modest release checks should only process new checksummed inputs or
  explicitly requested analysis versions. Avoid importing directly into the
  production Pausanias database as a side effect of publishing the atlas.
- Run heavy analyses in separate staged data, with stable job IDs, locking, time
  and memory limits, and declared LLM/GNN budgets. No costly work merely to prove
  that cron is running.
- Report new release, successful changed build or actionable failure to the
  existing channel. No routine no-change messages or duplicate channel required.
- Preserve current public output on failure; retain a reproducible release and
  rollback manifest. Before enabling cron, check read-only source permissions,
  forced-command key restrictions, atomic promotion/rollback, DNS/HTTPS, cache
  headers and one clearly labelled approved reporting test.

## Local implementation already prepared

`build_manto_atlas.py` creates a static preview from read-only queries. It does not
create accounts, roles, keys, DNS records, cron entries or Slack messages, and it
never deploys. The current prototype deliberately labels incomplete chronology,
entity resolution, automated claims and historical models; it must not be relabelled
as a fully validated survival/copying analysis during deployment.
