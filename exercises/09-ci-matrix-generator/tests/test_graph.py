"""Contract for the dependency graph. The exercise lives here.

The transitive test is the one that matters. Stopping at direct dependents is the
bug that makes the tool appear to work right up until the first two-level change
ships untested.
"""

from __future__ import annotations

import pytest

from ci_matrix.graph import build_graph, find_cycles, reverse_closure, services_for_paths
from ci_matrix.models import Service


class TestBuildGraph:
    def test_edges_point_at_dependencies(self, chain):
        graph = build_graph(chain)
        assert graph["shared-auth"] == frozenset({"shared-logging"})

    def test_a_service_with_no_dependencies_has_an_empty_edge_set(self, chain):
        assert build_graph(chain)["docs-site"] == frozenset()

    def test_an_unknown_dependency_is_a_loud_error(self):
        """Not a silently dropped edge.

        A dropped edge means the dependent stops being rebuilt when its
        dependency changes - which is the exact failure this tool prevents,
        arriving quietly. The error must name both services.
        """
        broken = {"api": Service(name="api", path="services/api", depends_on=("ghost",))}
        with pytest.raises(ValueError, match="ghost"):
            build_graph(broken)


class TestCycles:
    def test_a_two_node_cycle_is_detected(self, cyclic):
        assert find_cycles(build_graph(cyclic))

    def test_the_cycle_report_names_the_services(self, cyclic):
        """So the error message can be useful. A `RecursionError` from inside a CI
        job tells the reader nothing at all."""
        cycles = find_cycles(build_graph(cyclic))
        flat = {name for cycle in cycles for name in cycle}
        assert flat == {"a", "b"}

    def test_an_acyclic_graph_reports_no_cycles(self, chain):
        assert find_cycles(build_graph(chain)) == ()

    def test_a_self_dependency_is_a_cycle(self):
        selfdep = {"a": Service(name="a", path="services/a", depends_on=("a",))}
        assert find_cycles(build_graph(selfdep))


class TestReverseClosure:
    def test_a_direct_dependent_is_included(self, chain):
        affected = reverse_closure(build_graph(chain), ["shared-auth"])
        assert "checkout-api" in affected

    def test_the_closure_is_transitive(self, chain):
        """`shared-logging <- shared-auth <- checkout-api`.

        Changing the logging library must build all three. This is the test that
        separates a working tool from one that looks like it works.
        """
        affected = reverse_closure(build_graph(chain), ["shared-logging"])
        assert {"shared-auth", "checkout-api"} <= set(affected)

    def test_an_unrelated_service_is_not_included(self, chain):
        affected = reverse_closure(build_graph(chain), ["shared-logging"])
        assert "docs-site" not in affected

    def test_the_chain_is_recorded_not_just_the_name(self, chain):
        """`--explain` needs the chain. "checkout-api was included because
        shared-auth changed" is not an explanation when shared-auth did not change
        either - the reader has to be able to follow it back to shared-logging."""
        affected = reverse_closure(build_graph(chain), ["shared-logging"])
        assert "shared-logging" in affected["checkout-api"]
        assert "shared-auth" in affected["checkout-api"]

    def test_it_terminates_on_a_cyclic_graph(self, cyclic):
        """Either refuse, or track visited nodes - but do not recurse forever.

        Decide which and record it in `DECISIONS.md`. If you chose to refuse,
        change this test to assert the exception.
        """
        affected = reverse_closure(build_graph(cyclic), ["a"])
        assert "b" in affected

    def test_an_empty_root_set_affects_nothing(self, chain):
        assert reverse_closure(build_graph(chain), []) == {}


class TestPathAttribution:
    def test_a_source_file_maps_to_its_service(self, chain):
        owned = services_for_paths(chain, ["services/checkout-api/src/main.py"])
        assert "checkout-api" in owned

    def test_longest_prefix_wins(self, nested):
        """`services/api/main.py` belongs to `api` at `services/api`, not to
        `platform` at `services`. Sort candidates by length descending, or nested
        services silently attribute their changes to the parent."""
        owned = services_for_paths(nested, ["services/api/main.py"])
        assert set(owned) == {"api"}

    def test_a_file_owned_by_nobody_is_not_an_error(self, chain):
        """It might be documentation, or a global trigger. Both are handled
        elsewhere; return what matched and let the caller decide."""
        assert services_for_paths(chain, ["README.md"]) == {}

    def test_the_causing_files_are_recorded(self, chain):
        owned = services_for_paths(chain, ["services/checkout-api/src/main.py"])
        assert "services/checkout-api/src/main.py" in owned["checkout-api"]

    def test_a_deleted_file_still_attributes_to_its_service(self, chain):
        """Deleting a service's last source file is a change to that service.

        The path no longer exists on disk, so an implementation that stats the
        file instead of matching the string drops it - and the "change touching a
        deleted service" acceptance case fails.
        """
        owned = services_for_paths(chain, ["services/docs-site/index.md"])
        assert "docs-site" in owned
