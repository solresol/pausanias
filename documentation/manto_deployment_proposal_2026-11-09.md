# Epimanto deployment status and proposal

Initial inspection: 9 November 2026. Updated after the Epimanto name was chosen
and its dedicated restricted deployment key was approved, installed and tested.
The target remains empty and private. No database grant, DNS, vhost, cron or live
publication change has been made.

## Verified target and existing capability

- Chosen hostname `epimanto.symmachus.org`: DNS NXDOMAIN on recheck. The
  dedicated publishing directory now exists; no vhost has been installed.
  The existing sibling-site convention is a proxied
  Cloudflare A record, TTL 1. Recheck its configured origin during provisioning.
- Existing repository: `https://github.com/solresol/pausanias.git`. Public read
  access requires no new Git credential. Atlas source lives under `manto_atlas/`.
- Raksasa: Linux, existing Greg sudo access verified. The unprivileged
  `epimanto` service account now exists, with a locked password, nologin shell,
  no supplementary groups and private home `/var/lib/epimanto`.
- Merah: OpenBSD; Greg SSH and doas access verified.
  Use doas, not Linux-specific sudo commands. Its `epimanto` publishing account
  has no supplementary groups and no password login. Its home and authorized
  key file are root-controlled and cannot be changed by the account.
- Existing Merah httpd serves Pausanias under
  `/var/www/vhosts/pausanias.symmachus.org/htdocs/`; relayd exposes public HTTP and
  forwards to an internal httpd listener.
- Existing Pausanias HTTPS works through Cloudflare. No origin IPv4 443 listener
  was observed. The actual zone TLS policy is unverified; do not assume strict
  origin TLS or change a zone-wide setting to make this site work.
- Existing reporting destination is
  [#pausanias](https://ifost.slack.com/archives/C0CDAQ68FV2), channel `C0CDAQ68FV2`.
  The existing service-owned webhook file is private; its contents were not read.
- PG18 is on `/var/run/postgresql`, port 5433, database `pausanias`. Manual read
  queries work as Greg. The `epimanto` DB role does not exist. Role-specific
  authentication isolation must precede enabling that login: allow only the
  existing local socket and Pausanias database, rejecting other database,
  TCP and replication connections. This additional configuration step awaits
  separate approval. Greg's superuser capability is not an appropriate grant
  for the new job.

## Installed key and remaining access scope

1. Raksasa's `epimanto` account owns a dedicated Ed25519 key in its private SSH
   directory. Home and SSH directory are 0700; private key is 0600. The private
   key never leaves Raksasa. No sudo access or personal key reuse was granted.
2. Merah's `epimanto` key is forced through
   `rrsync -wo -munge /var/www/vhosts/epimanto.symmachus.org/htdocs`, with the
   OpenSSH `restrict` option. The htdocs directory is private, mode 0700;
   its parent is root-controlled and not writable by the publishing account.
3. The existing authenticated Merah host identity was pinned. A harmless upload
   was verified and removed. Shell, download, traversal, escaping temporary
   directories, symlink escape, PTY and TCP-forwarding tests were denied.
   Uploaded symlinks were made inert. This is the standard rrsync application
   restriction, not an OS chroot. The key may write/delete within its site scope;
   future publishing scripts must not use broad deletion or overwrite old
   content-addressed releases.
4. `prepare_epimanto_release.py` prepares assets under a content-addressed
   `_releases/` directory and a root index referencing those exact assets.
   Upload assets successfully before the final root-index switch; serialize
   the two steps and retain prior assets. The root file rename can be atomic,
   but rsync is not a multi-file transaction. This needs no broader key access.
5. If using live source reads, a peer-authenticated, non-superuser DB role
   `epimanto`, CONNECT to the existing database, and schema USAGE/SELECT only on
   the explicitly chosen source tables. The current v3 snapshot needs
   `manto_releases`, `manto_entity_details` and `manto_edges` in the completed
   v3 staging schema, plus these six existing public tables:
   `manto_place_links`, `pleiades_places`, `passages`, `translations`,
   `passage_place_state_mentions`, `place_survival_model_runs`.
   No table writes, sequence privileges, role administration, creation rights or
   access to unrelated tables. Default read-only transactions and bounded query
   timeouts are guardrails, not an authorization boundary: validate privileges
   independently of those defaults, including inherited PUBLIC rights across
   the shared cluster. The login must not be enabled before its connection
   isolation is verified. A service-produced export snapshot could avoid a new live DB grant,
   but its access and scheduled export ownership must be designed explicitly.
6. Existing-channel Slack reporting under job ID `epimanto`, through a
   separately approved scoped credential/service. Do not make the existing
   Pausanias webhook world/group-readable or copy secret values into Git.

The approved key/account scope is complete. Database access, public serving
permissions, DNS/network changes and any reporting credential expansion still
need their own approval. The first static snapshot can be published without
granting live database access; automatic source refresh is a separate step.

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
