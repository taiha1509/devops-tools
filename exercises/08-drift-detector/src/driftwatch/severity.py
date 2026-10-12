"""Blast-radius ranking. Pure, and configurable - because the defaults are wrong.

A replaced RDS instance and a replaced CloudWatch alarm are not the same event.
Ranking them identically is what makes a 900-line plan unreadable: everything is
either "a change" or it isn't, so reviewers stop looking.

You **will** get the defaults wrong for someone's stack. The point of making the
map configurable is not flexibility for its own sake - it is that the first time
this tool annoys a team, they can fix it in a YAML file instead of filing an
issue against you and going back to not reading plans.

YOUR JOB: implement `severity_for`, `load_severity_map` and `apply_severities`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from driftwatch.models import Severity

if TYPE_CHECKING:
    from pathlib import Path

    from driftwatch.models import ChangeKind, PlanReport

DEFAULT_SEVERITY_MAP: dict[str, Severity] = {
    # Stateful. Replacing these destroys data or breaks every connection to it.
    "aws_db_instance": Severity.CRITICAL,
    "aws_rds_cluster": Severity.CRITICAL,
    "aws_elasticache_cluster": Severity.CRITICAL,
    "aws_dynamodb_table": Severity.CRITICAL,
    "aws_s3_bucket": Severity.CRITICAL,
    "aws_ebs_volume": Severity.CRITICAL,
    # Networking. Replacing these is usually an outage even though nothing is lost.
    "aws_vpc": Severity.HIGH,
    "aws_subnet": Severity.HIGH,
    "aws_nat_gateway": Severity.HIGH,
    "aws_lb": Severity.HIGH,
    "aws_lb_listener": Severity.HIGH,
    "aws_route53_record": Severity.HIGH,
    # Security. Low blast radius to change, high consequence to get wrong - which
    # is a different axis from the others. Decide whether your severity means
    # "how much breaks" or "how carefully should a human read this", and write
    # the answer down, because these entries only make sense under the second.
    "aws_security_group": Severity.HIGH,
    "aws_security_group_rule": Severity.HIGH,
    "aws_iam_role": Severity.HIGH,
    "aws_iam_policy": Severity.HIGH,
    # Compute. Replaceable by design, usually behind a load balancer.
    "aws_instance": Severity.MEDIUM,
    "aws_ecs_service": Severity.MEDIUM,
    "aws_lambda_function": Severity.MEDIUM,
    "aws_autoscaling_group": Severity.MEDIUM,
    # Observability and metadata. Churn here is noise.
    "aws_cloudwatch_metric_alarm": Severity.LOW,
    "aws_cloudwatch_log_group": Severity.LOW,
    "aws_ssm_parameter": Severity.LOW,
}

DEFAULT_UNKNOWN_SEVERITY = Severity.MEDIUM
"""Unknown resource types get MEDIUM, never a crash.

MEDIUM rather than LOW on purpose: an unranked type is an *unknown* blast radius,
and the safe direction for an unknown is "a human should look at this". Defaulting
unknowns to LOW means every new resource type is invisible until someone notices.

This is the same asymmetry question E09 asks about its matrix - when the tool is
wrong, which direction should it be wrong in? Write the answer in `DECISIONS.md`.
"""


def load_severity_map(path: Path | None) -> dict[str, Severity]:
    """Merge a YAML override file over `DEFAULT_SEVERITY_MAP`.

    `path=None` returns the defaults. Merge rather than replace - a team wanting
    to bump one resource type should not have to restate the other twenty-four.

    Expected shape::

        aws_instance: critical       # we run stateful workloads on EC2
        aws_cloudwatch_metric_alarm: info

    Reject an unknown severity name with a message listing the valid ones. A
    typo'd `criticial` silently falling back to the default is how someone's
    override quietly stops working.
    """
    raise NotImplementedError


def severity_for(
    resource_type: str,
    kind: ChangeKind,
    *,
    severity_map: dict[str, Severity] | None = None,
) -> Severity:
    """Severity of one change.

    The ranking is two-dimensional and that is the interesting part: severity
    comes from the resource type, then **the kind modulates it**. Creating an RDS
    instance is not the same event as destroying one, even though the type is
    identical.

    A workable rule, which you should argue with:

        DESTROY / REPLACE  full severity from the map
        UPDATE             one step down - in-place updates are usually safe
        CREATE             one step down again - new things break less
        NO_OP / READ       INFO

    What this rule gets wrong: an in-place update to a security group rule can
    open your database to the internet, which is not "one step down" from
    anything. Decide whether to special-case it and record the decision.
    """
    raise NotImplementedError


def apply_severities(
    report: PlanReport,
    *,
    severity_map: dict[str, Severity] | None = None,
) -> PlanReport:
    """Return a copy of `report` with severities assigned and changes sorted.

    Also populate `unknown_types` with any resource type that was not in the map,
    so the comment can say the ranking was a guess. Sort by
    `ResourceChange.sort_key()` - severe first, which is the only ordering that
    makes a long plan readable.
    """
    raise NotImplementedError


__all__ = [
    "DEFAULT_SEVERITY_MAP",
    "DEFAULT_UNKNOWN_SEVERITY",
    "apply_severities",
    "load_severity_map",
    "severity_for",
]
