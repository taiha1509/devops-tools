# Plan fixtures

Committed `terraform show -json` output. **No Terraform binary in the test suite,
no AWS, no emulator** — which is also why this exercise is not blocked by the
LocalStack situation described in the roadmap.

These seven are hand-built to the documented
[JSON plan format](https://developer.hashicorp.com/terraform/internals/json-format)
so the suite runs the moment you clone it. They are faithful in shape but small;
replace any of them with real captured output whenever you have it, since real
plans have module nesting and `after_unknown` blocks far messier than these.

| Fixture | Case | What it is for |
|---|---|---|
| `no-changes.json` | all `no-op`, plus a data-source `read` | Clean plan. The `read` entry must not be counted as a change. |
| `creates-only.json` | three `create`s, one inside a module | Exit 1, nothing destructive. `module_address` is present on one. |
| `update-in-place.json` | two `update`s | One is a security-group rule opening `0.0.0.0/0` — the case that argues against "updates are one step down". |
| `replace.json` | **both** replace orderings | `["delete","create"]` and `["create","delete"]`. An implementation checking only the first misses every `create_before_destroy` resource. |
| `destroy.json` | two `delete`s | Exit 2 under the default `--fail-on destructive`. |
| `empty.json` | no `resource_changes` key at all | Not an empty array — **absent**. `document["resource_changes"]` raises here. |
| `unknown-type.json` | `snowflake_warehouse`, `datadog_monitor` | Neither is in the severity map. Must get the documented default, never crash. |
| `true-drift.json` | `resource_drift` + a plan that reverts it | The 3am console fix about to be undone, alongside an ordinary intentional diff. |

## Capturing real output

```bash
terraform plan -out=tf.plan
terraform show -json tf.plan > tests/fixtures/plans/<case>.json
```

Scrub before committing: account IDs, ARNs, IP ranges, bucket names, and anything
under `after` for a secret-bearing resource. A plan file is a fairly complete
description of your infrastructure.

If a captured plan is enormous, trim `resource_changes` down to the entries the
test needs rather than committing 40MB. Keep `format_version` and
`terraform_version` intact — `load_plan` checks them.
