# Security Policy

This standalone fy-suites workspace treats secrets, provider credentials,
private keys, generated run state, and imported reference bundles as
non-source artifacts.

Report suspected exposure or unsafe generated content to the repository
maintainer before widening distribution. Remove exposed values from the
tracked tree, rotate the affected credential out of band, and rerun
`fy-platform production-readiness` plus `fy-platform analyze --mode security`
before release.

The workspace `.gitignore` blocks common secret-bearing file names and private
key extensions. Keep additional local credentials in an external secret store
or environment manager.

