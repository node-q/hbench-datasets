# Security

To report a problem with a published dataset, use GitHub's private vulnerability reporting:
[Report a vulnerability](https://github.com/node-q/hbench-datasets/security/advisories/new), on this
repository's Security tab. Please don't open a public issue.

Problems worth reporting include a signature or attestation that does not verify, a tag that
resolves to a different digest than before, a task that contains malicious code or a secret, and a
dataset published against its licence. Include the reference and its digest
(`oras resolve ghcr.io/node-q/hbench-datasets/<dataset>:<version>`), what you ran, and what you saw.

Published versions are never changed. When one is bad, we publish a fixed version and name the
affected versions in the advisory.

Problems in hbench itself go to [node-q/hbench](https://github.com/node-q/hbench).
