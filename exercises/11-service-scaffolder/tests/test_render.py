"""Contract for rendering, and for the templates themselves.

**Templates are testable.** Rendering every template with representative inputs,
then running the generated project's own lint and tests, is a test you can and
should automate. A scaffolder that emits code failing its own standards is worse
than no scaffolder - it makes "correct" mean "whatever the generator did".
"""

from __future__ import annotations

import pytest
from jinja2 import UndefinedError

from scaffolder.models import GENERATED_MARKER
from scaffolder.render import render_template, template_context
from scaffolder.templates import available_templates, load_template_version


class TestTemplateDiscovery:
    def test_both_shipped_templates_are_found(self, templates_root, version):
        """Two templates, so the abstraction is proven rather than assumed."""
        assert set(available_templates(templates_root)) >= {"python-fastapi", "python-worker"}

    def test_the_list_is_sorted(self, templates_root, version):
        """E10's `UnknownTemplate` error renders this list. An unstable order
        makes the error message different on every run."""
        found = available_templates(templates_root)
        assert list(found) == sorted(found)

    def test_every_template_declares_a_version(self, templates_root, version):
        """A template that cannot say what version it is cannot be managed, which
        makes `--check` meaningless for every service it generates."""
        for name in available_templates(templates_root):
            assert load_template_version(templates_root / name).version


class TestContext:
    def test_module_is_the_importable_form_of_the_name(self, spec, version):
        """`payments-api` is not an importable Python module. Getting this wrong
        produces a service that fails on its first import, which at least fails
        loudly - unlike most of the bugs in this exercise."""
        context = template_context(spec, version)
        assert context["module"] == "payments_api"

    def test_the_context_has_no_timestamp(self, spec, version):
        """Deliberately absent.

        A timestamp in generated output makes regeneration non-idempotent, so
        `--check` reports drift on every service every day, the signal becomes
        useless, and people stop running it. Creation dates belong in the stamp
        file, which is written once.
        """
        context = template_context(spec, version)
        assert not any("time" in k or "date" in k or "now" in k for k in context)


class TestRendering:
    def test_rendering_writes_nothing(self, fastapi_template, spec, tmp_path, version):
        """Everything renders in memory first. That ordering is the only reason
        "fail before writing a single file" is achievable."""
        render_template(fastapi_template, spec, version)
        assert list(tmp_path.iterdir()) == []

    def test_paths_are_themselves_rendered(self, fastapi_template, spec, version):
        """`src/{{ module }}/main.py` -> `src/payments_api/main.py`."""
        rendered = render_template(fastapi_template, spec, version)
        assert any(f.path == "src/payments_api/main.py" for f in rendered)

    def test_generated_files_carry_the_marker(self, fastapi_template, spec, version):
        """The marker is the ownership contract, and it has to be visible in the
        file itself to a human reading it in six months."""
        rendered = render_template(fastapi_template, spec, version)
        dockerfile = next(f for f in rendered if f.path == "Dockerfile")
        assert GENERATED_MARKER in dockerfile.content

    def test_team_owned_files_do_not_carry_the_marker(self, fastapi_template, spec, version):
        """`main.py` is seeded once and then the team's. A marker on it would
        invite regeneration to clobber the actual service."""
        rendered = render_template(fastapi_template, spec, version)
        main = next(f for f in rendered if f.path.endswith("main.py"))
        assert GENERATED_MARKER not in main.content
        assert main.generated is False

    def test_output_order_is_stable(self, fastapi_template, spec, version):
        first = render_template(fastapi_template, spec, version)
        second = render_template(fastapi_template, spec, version)
        assert [f.path for f in first] == [f.path for f in second]

    def test_rendering_twice_produces_identical_content(self, fastapi_template, spec, version):
        """Idempotence at the render level, which is what `--check` depends on."""
        first = render_template(fastapi_template, spec, version)
        second = render_template(fastapi_template, spec, version)
        assert [f.content for f in first] == [f.content for f in second]

    def test_an_undefined_variable_raises_rather_than_rendering_empty(
        self, tmp_path, spec, version
    ):
        """`StrictUndefined`, and the most valuable line in `build_environment`.

        By default Jinja2 renders an unknown variable as the empty string, so a
        typo'd `{{ tem }}` produces a Dockerfile with a blank `FROM` line and no
        error at all. Generating broken-but-plausible files silently is the worst
        failure this tool has available.
        """
        template_dir = tmp_path / "broken"
        (template_dir / "").mkdir(parents=True, exist_ok=True)
        (template_dir / "template.yaml").write_text(
            'name: broken\nversion: "1.0.0"\nfiles:\n'
            '  - src: "x.j2"\n    path: "x"\n    generated: true\n'
        )
        (template_dir / "x.j2").write_text("FROM {{ nonexistent_variable }}\n")
        with pytest.raises(UndefinedError):
            render_template(template_dir, spec, version)

    def test_files_end_with_a_newline(self, fastapi_template, spec, version):
        """`keep_trailing_newline=True`. Without it every generated file is
        missing its final newline and every first commit has a noisy diff."""
        rendered = render_template(fastapi_template, spec, version)
        assert all(f.content.endswith("\n") for f in rendered)


class TestBothTemplatesRenderThroughTheSameCode:
    """The reason there are two templates.

    Every hardcoded assumption about FastAPI, HTTP ports and healthz endpoints
    looks like generic scaffolding until a genuinely different service type has
    to render through the same code.
    """

    def test_the_worker_template_renders(self, worker_template, make_spec, version):
        spec = make_spec(name="charge-worker", template="python-worker")
        rendered = render_template(worker_template, spec, version)
        assert rendered

    def test_the_worker_has_no_http_surface(self, worker_template, make_spec, version):
        """If `render_template` needed a special case to make python-fastapi work,
        this is where it shows up."""
        spec = make_spec(name="charge-worker", template="python-worker")
        rendered = render_template(worker_template, spec, version)
        dockerfile = next(f for f in rendered if f.path == "Dockerfile")
        assert "EXPOSE" not in dockerfile.content


class TestGeneratedProjectMeetsItsOwnStandards:
    """The acceptance criterion with the most teeth.

    Generate into `tmp_path`, then run the generated project's own
    `ruff check` / `mypy --strict` / `pytest` as a subprocess and assert exit 0.
    Slow, so mark it, but do not skip it: a scaffolder emitting code that fails
    its own quality bar teaches every new service that the bar is optional.
    """

    @pytest.mark.slow
    def test_generated_fastapi_service_passes_ruff(self, fastapi_template, spec, tmp_path, version):
        raise AssertionError("implement: generate into tmp_path, subprocess ruff check, assert 0")

    @pytest.mark.slow
    def test_generated_fastapi_service_passes_mypy(self, fastapi_template, spec, tmp_path, version):
        raise AssertionError("implement: subprocess mypy --strict src, assert 0")

    @pytest.mark.slow
    def test_generated_worker_service_passes_ruff(
        self, worker_template, make_spec, tmp_path, version
    ):
        raise AssertionError("implement: same, for python-worker")
