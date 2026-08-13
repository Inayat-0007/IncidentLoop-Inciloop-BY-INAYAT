# Sample bundle source

Anonymized snapshot **inspired by** the public GitLab.com database incident postmortem (2017-01-31 / published 2017-02-10):

https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/

No customer data, no GitLab credentials, no copied internal telemetry. Service names (`web-api`) and numbers (`error_rate` 12.7, `latency_ms` 890) are illustrative of a post-deploy database failure pattern — not GitLab’s real metrics.

Live investigate uses `data/company/metrics.json` (and logs/releases) when those files exist; otherwise this sample loads with `data_mode: sample_bundle`.
