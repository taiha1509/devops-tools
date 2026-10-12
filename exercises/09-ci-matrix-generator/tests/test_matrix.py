"""Contract for planning and matrix emission.

The safety question from the brief runs through every test here: **when this tool
is wrong, which direction should it be wrong in?** Building too much wastes money.
Building too little ships untested code. That asymmetry drives every default, and
each test below pins one of those decisions.
"""

from __future__ import annotations

import json

from ci_matrix.graph import build_graph
from ci_matrix.matrix import MATRIX_JOB_LIMIT, explain, plan_builds, to_matrix
from ci_matrix.models import Reason, Service


class TestAcceptanceShapes:
    """The five repo shapes named in the brief's acceptance criteria."""

    def test_a_leaf_change_builds_only_that_service(self, chain):
        plan = plan_builds(chain, ["services/checkout-api/src/main.py"])
        assert plan.services == ("checkout-api",)

    def test_a_shared_library_change_builds_the_whole_closure(self, chain):
        plan = plan_builds(chain, ["libs/shared-logging/log.py"])
        assert set(plan.services) == {"shared-logging", "shared-auth", "checkout-api"}

    def test_a_global_trigger_builds_everything(self, chain):
        plan = plan_builds(chain, [".github/workflows/ci.yaml"])
        assert set(plan.services) == set(chain)
        assert all(i.reason is Reason.GLOBAL_TRIGGER for i in plan.inclusions)

    def test_a_docs_only_change_builds_nothing(self, chain):
        plan = plan_builds(chain, ["README.md", "docs/architecture.md"])
        assert plan.empty is True

    def test_a_change_touching_a_deleted_service(self, chain):
        """The service's directory is gone from disk but its files are in the diff.

        An implementation that stats paths instead of matching strings drops this
        silently - and "silently" is the problem: deleting a service should run
        its CI one last time, or at minimum not be invisible.
        """
        plan = plan_builds(chain, ["services/docs-site/index.md"])
        assert "docs-site" in plan.services


class TestSafeDegradation:
    def test_an_unparseable_manifest_builds_everything(self, chain):
        """Never "build nothing".

        If the graph might be incomplete, no conclusion drawn from it is safe -
        so this check comes before everything else in `plan_builds`.
        """
        plan = plan_builds(
            chain,
            ["services/checkout-api/src/main.py"],
            unparseable=("services/web/ci-service.yaml",),
        )
        assert set(plan.services) == set(chain)
        assert plan.degraded is True

    def test_degradation_is_always_visible(self, chain):
        """A tool that silently degrades to build-all has quietly become the
        40-minute CI run it was written to replace, and nobody will know why."""
        plan = plan_builds(chain, ["x.py"], unparseable=("broken.yaml",))
        assert plan.degraded_reason

    def test_exceeding_the_job_limit_degrades_rather_than_emitting_an_invalid_matrix(self):
        """Over 256 jobs, GitHub fails the **whole run** - it does not truncate.

        On a monorepo that means CI is broken for everyone until someone notices.
        """
        many = {
            f"svc-{n:03d}": Service(name=f"svc-{n:03d}", path=f"services/svc-{n:03d}")
            for n in range(300)
        }
        plan = plan_builds(many, [".github/workflows/ci.yaml"])
        assert plan.degraded is True

    def test_the_job_limit_counts_extra_dimensions_not_just_services(self):
        """20 services with a 4-way Python axis is 80 jobs, not 20.

        Counting services alone passes the check and then fails the run, which is
        the worst place to find out.
        """
        wide = {
            f"svc-{n:02d}": Service(
                name=f"svc-{n:02d}",
                path=f"services/svc-{n:02d}",
                extra={"python": ("3.11", "3.12", "3.13", "3.14")},
            )
            for n in range(80)
        }
        plan = plan_builds(wide, [".github/workflows/ci.yaml"], job_limit=MATRIX_JOB_LIMIT)
        assert plan.degraded is True


class TestMatrixEmission:
    def test_an_empty_plan_is_valid_json_with_an_empty_include(self, chain):
        """The acceptance criterion most likely to bite in week one.

        `{}`, `null`, or an empty string makes the downstream job **fail** rather
        than skip, which turns every docs-only PR into a red build.
        """
        plan = plan_builds(chain, ["README.md"])
        matrix = to_matrix(plan, services=chain)
        assert matrix == {"include": []}
        json.dumps(matrix)  # must be serialisable

    def test_include_entries_carry_the_service_and_its_path(self, chain):
        plan = plan_builds(chain, ["services/checkout-api/src/main.py"])
        matrix = to_matrix(plan, services=chain)
        assert matrix["include"][0]["service"] == "checkout-api"
        assert matrix["include"][0]["path"] == "services/checkout-api"

    def test_extra_dimensions_expand_into_separate_entries(self):
        """`include` form rather than bare lists, because a cartesian product over
        the union of everyone's dimensions generates combinations that do not
        exist."""
        services = {
            "api": Service(name="api", path="services/api", extra={"python": ("3.12", "3.13")}),
        }
        plan = plan_builds(services, ["services/api/main.py"])
        matrix = to_matrix(plan, services=services)
        assert len(matrix["include"]) == 2

    def test_output_is_deterministic(self, chain):
        """An unstable order makes the Actions UI unreadable and breaks
        required-check names between runs."""
        plan = plan_builds(chain, ["libs/shared-logging/log.py"])
        first = json.dumps(to_matrix(plan, services=chain))
        second = json.dumps(to_matrix(plan, services=chain))
        assert first == second


class TestExplain:
    def test_it_states_the_reason_for_an_inclusion(self, chain):
        plan = plan_builds(chain, ["services/checkout-api/src/main.py"])
        assert "checkout-api" in explain(plan)

    def test_it_explains_exclusions_too(self, chain):
        """The question people actually ask is "why did my service **not** build",
        and a tool that only explains inclusions cannot answer it."""
        plan = plan_builds(chain, ["services/checkout-api/src/main.py"])
        assert "docs-site" in explain(plan)

    def test_a_transitive_inclusion_shows_the_whole_chain(self, chain):
        plan = plan_builds(chain, ["libs/shared-logging/log.py"])
        output = explain(plan)
        assert "shared-logging" in output
        assert "checkout-api" in output

    def test_it_is_readable_by_someone_who_has_never_seen_the_tool(self, chain):
        """An acceptance criterion that cannot be fully asserted - so this test is
        a reminder, not a check. Read your own output cold and decide. Dumping the
        `Plan` model fails the criterion even though it would pass any assertion
        you could write here.
        """
        raise AssertionError("implement: read the --explain output cold, then assert its shape")


def test_global_triggers_err_on_the_side_of_building(chain):
    """The lockfile case. A dependency bump changes nothing under any service
    directory, and every service's build is affected by it.

    Leaving lockfiles out of the triggers is the quiet version of this tool's
    worst failure: nothing errors, CI is fast, and the upgrade is untested.
    """
    plan = plan_builds(chain, ["uv.lock"])
    assert set(plan.services) == set(chain)


def test_graph_construction_is_separate_from_planning(chain):
    """Sanity check on the layering: the graph is pure and reusable, which is what
    lets `--explain` and `plan` share one source of truth."""
    assert build_graph(chain)["checkout-api"] == frozenset({"shared-auth"})
