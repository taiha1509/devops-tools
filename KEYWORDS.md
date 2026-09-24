# Python keywords & vocabulary — recall sheet

Companion to the [exercise track](README.md). Not a tutorial — a list of the names worth holding in
your head so you write Python instead of translating from Bash. Grouped by *what they're for*,
because that's how you'll reach for them.

Targets Python 3.12+ (what `uv` gives you here). Version notes are marked where it matters.

---

## 1. The 35 reserved keywords

You cannot use these as variable names. That's the whole definition — everything else below is a
name you *could* shadow, and shouldn't.

### Values (3)

| Keyword | Meaning |
|---|---|
| `True` / `False` | The two bools. Capitalised. `True == 1` is genuinely `True`. |
| `None` | Absence of a value. The only instance of `NoneType`. Test with `is None`, never `== None`. |

### Boolean & identity operators (5)

| Keyword | Meaning |
|---|---|
| `and` / `or` | Short-circuit. They return an **operand**, not a bool: `a or "default"` yields `a` if truthy. |
| `not` | Negation. `not x` is not the same as `x is False`. |
| `is` | Same object in memory. Use for `None`, `True`, `False`, sentinels — never for numbers or strings. |
| `in` | Membership (`x in list`) and the loop binder (`for x in ...`). `in` on a `set`/`dict` is O(1); on a `list` it's O(n) — this is the single easiest speedup in log-processing code. |

### Control flow (8)

| Keyword | Meaning |
|---|---|
| `if` / `elif` / `else` | Branching. No switch statement — see `match` below. |
| `for` / `while` | Loops. `for` iterates anything iterable; `while` repeats on a condition. |
| `break` | Leave the innermost loop now. |
| `continue` | Skip to the next iteration. |
| `pass` | Do nothing. A syntactic placeholder, for empty bodies and `...` stubs. |

**The one people forget:** `for ... else` and `while ... else`. The `else` runs **only if the loop
finished without `break`**. It's the clean "searched everything, found nothing" branch:

```python
for candidate in buckets:
    if candidate.name == wanted:
        break
else:
    raise LookupError(f"no bucket named {wanted}")
```

### Functions (4)

| Keyword | Meaning |
|---|---|
| `def` | Define a function. |
| `return` | Exit a function with a value. Bare `return` → `None`; falling off the end → `None`. |
| `lambda` | One-expression anonymous function. Fine as a `key=`; if it needs a name, use `def`. |
| `yield` | Makes the function a **generator** — lazy, one item at a time, constant memory. `yield from` delegates to another iterable. This is *the* keyword for log files bigger than RAM. |

### Classes & scope (4)

| Keyword | Meaning |
|---|---|
| `class` | Define a type. For plain data, reach for `@dataclass` first. |
| `global` | Rebind a module-level name from inside a function. A smell; pass arguments instead. |
| `nonlocal` | Rebind a name in the enclosing function's scope. Rare, and usually a sign you want a class. |
| `del` | Unbind a name (`del x`) or remove an item (`del d["key"]`). Does not "free memory" — it drops one reference. |

### Errors & cleanup (4)

| Keyword | Meaning |
|---|---|
| `try` | Guard a block. |
| `except` | Handle a raised exception. `except (A, B) as e:` catches either. |
| `finally` | Runs no matter what — exception, `return`, or `break`. For cleanup that must not be skipped. |
| `raise` | Throw. Bare `raise` inside `except` re-raises the original with its traceback intact. `raise X from err` keeps the cause chain. |

Also: `try/except/else` — the `else` block runs only when nothing raised, so you can keep the
`try` down to the single line that might actually fail.

```python
try:
    payload = json.loads(raw)
except json.JSONDecodeError as err:
    raise ConfigError(f"{path} is not valid JSON") from err
else:
    return payload
finally:
    handle.close()
```

`except*` (3.11+) catches from an `ExceptionGroup` — what `asyncio.TaskGroup` raises when several
concurrent tasks fail at once.

### Context managers (2)

| Keyword | Meaning |
|---|---|
| `with` | Acquire/release around a block. Files, locks, temp dirs, DB transactions, `mock.patch`. If you're writing `try/finally` to close something, `with` already exists for it. |
| `as` | Binds a name — in `with ... as`, `except ... as`, and `import ... as`. |

```python
with open(path) as fh, tempfile.TemporaryDirectory() as tmp:   # multiple in one with
    ...
```

### Imports (3)

| Keyword | Meaning |
|---|---|
| `import` | Load a module. |
| `from` | Select names out of a module — also `yield from` and `raise ... from`. |
| `as` | Alias (see above). |

### Assertions (1)

| Keyword | Meaning |
|---|---|
| `assert` | Raise `AssertionError` if false. **Stripped entirely by `python -O`** — so it belongs in tests and internal invariants, never in input validation or a security check. |

### Async (2)

| Keyword | Meaning |
|---|---|
| `async` | `async def`, `async for`, `async with`. |
| `await` | Suspend until an awaitable resolves. Only legal inside `async def`. |

Worth knowing, but for most infra work `concurrent.futures.ThreadPoolExecutor` over boto3 calls is
simpler and fast enough — the bottleneck is network I/O, not the GIL.

---

## 2. Soft keywords (4)

Contextual — still usable as variable names, which is exactly why they're easy to miss.

| Keyword | Meaning |
|---|---|
| `match` / `case` | Structural pattern matching (3.10+). Destructures shapes, not just values — genuinely good for event payloads and CLI dispatch. |
| `_` | Wildcard pattern inside `case _:` (the default arm). Elsewhere it's just a convention for "unused". |
| `type` | Type-alias statement (3.12+): `type Findings = dict[str, list[Path]]`. Distinct from the `type()` builtin. |

```python
match event:
    case {"source": "aws.ec2", "detail": {"state": "terminated", "instance-id": iid}}:
        reap(iid)
    case {"source": str(src)} if src.startswith("aws."):
        log.info("unhandled aws event", extra={"source": src})
    case _:
        raise ValueError("unknown event shape")
```

---

## 3. Not keywords, but you must know them

### Operators worth naming

- `:=` — **walrus**. Assign inside an expression: `while chunk := fh.read(8192):`.
- `*args` / `**kwargs` — variadic positional/keyword params. Also unpacking: `f(*items)`, `{**a, **b}`.
- `/` and `*` in a signature — positional-only and keyword-only markers: `def f(a, /, b, *, c)`.
- `@decorator` — wraps a function/class. `@property`, `@staticmethod`, `@classmethod`,
  `@functools.cache`, `@dataclass`, `@pytest.fixture`, `@contextmanager`.
- `->` — return annotation. `mypy --strict` requires it on every function, including `-> None`.
- `f"{value!r}"` and `f"{count=}"` — repr conversion, and the debug specifier that prints
  `count=3`. `f"{ratio:.2%}"`, `f"{size:>10,}"` for alignment/thousands.

### Comprehensions

```python
stale = [p for p in root.rglob("*.log") if age_days(p) > 30]        # list
by_ext = {p.suffix for p in paths}                                   # set
sizes  = {p.name: p.stat().st_size for p in paths}                   # dict
total  = sum(p.stat().st_size for p in paths)                        # generator — no list built
```

### Builtins you should reach for by reflex

`len` `range` `enumerate` `zip` `sorted` `reversed` `sum` `min` `max` `any` `all` `abs` `round`
`map` `filter` `isinstance` `getattr` `setattr` `hasattr` `repr` `open` `print` `int` `str` `float`
`bool` `list` `dict` `set` `tuple` `frozenset` `type` `vars` `dir` `id` `next` `iter` `super`

The high-leverage four: `enumerate(xs, start=1)` instead of a counter, `zip(a, b, strict=True)`
(3.10+) instead of indexing, `any`/`all` over a generator instead of a flag variable, and
`sorted(xs, key=..., reverse=True)` instead of hand-rolled sorting.

### Dunders you'll actually type

`__init__` `__repr__` `__eq__` `__hash__` `__enter__`/`__exit__` `__iter__`/`__next__` `__len__`
`__call__` `__name__` `__main__` `__file__` `__doc__` `__all__` `__slots__`

```python
if __name__ == "__main__":
    sys.exit(main())
```

---

## 4. Typing vocabulary (the track runs `mypy --strict`)

| Name | Use |
|---|---|
| `X \| None` | Modern `Optional[X]`. Prefer the pipe. |
| `list[str]`, `dict[str, int]` | Builtin generics — no `typing.List` since 3.9. |
| `Sequence` / `Iterable` / `Iterator` / `Mapping` | Accept the *widest* type in params, return the concrete one. Taking `Iterable[str]` instead of `list[str]` is the single biggest typing upgrade in ordinary code. |
| `Any` | Escape hatch. Every one is a hole in your type coverage — justify it. |
| `cast(T, x)` | "Trust me" with zero runtime cost. |
| `Literal["dry-run", "apply"]` | Fixed string choices. |
| `TypedDict` | Shape of a JSON/API dict. |
| `Protocol` | Structural typing — duck typing that mypy can check. |
| `Final` | Constant; mypy rejects rebinding. |
| `Self` (3.11+) | Return type of chainable/alternate constructors. |
| `NoReturn` / `Never` | Function never returns normally (it raises or exits). |
| `TypeVar` / generic `def f[T](x: T) -> T` (3.12+) | Generic functions. |
| `NewType` | A distinct `BucketName` that isn't interchangeable with any old `str`. |
| `@overload` | Different signatures for different arg shapes. |

---

## 5. Stdlib modules to know by name for infra work

| Module | What you use it for |
|---|---|
| `pathlib` | `Path`, `.rglob()`, `.stat().st_mtime`/`.st_size`, `.unlink(missing_ok=True)`, `.is_symlink()`, `/` joining. Replaces almost all of `os.path`. |
| `os` | `os.environ.get("AWS_REGION", "us-east-1")`, `os.getenv`, `os.walk` (when you need `topdown` control `rglob` can't give). |
| `shutil` | `disk_usage`, `rmtree`, `copy2`, `which`. |
| `subprocess` | `run(cmd, check=True, capture_output=True, text=True)`. Pass a **list**, avoid `shell=True`. |
| `argparse` | CLIs. Exits `2` on bad usage — that's the convention worth preserving. |
| `logging` | `getLogger(__name__)`, `basicConfig`, `extra={...}` for structured fields. Never `print` in a library. |
| `json` / `csv` / `tomllib` (3.11+, read-only) | Serialisation; `tomllib` reads `pyproject.toml`. |
| `dataclasses` | `@dataclass(frozen=True, slots=True)`, `field(default_factory=list)`. |
| `enum` | `Enum`, `StrEnum` (3.11+) for stringly-typed states. |
| `datetime` | `datetime.now(UTC)` — `utcnow()` is deprecated and returns a naive datetime, which is the root of most timezone bugs. `timedelta`, `.fromisoformat()`. |
| `contextlib` | `@contextmanager`, `suppress`, `ExitStack`, `chdir` (3.11+). |
| `functools` | `cache`, `lru_cache`, `partial`, `wraps`, `cached_property`. |
| `itertools` | `islice`, `chain`, `groupby` (needs sorted input!), `batched` (3.12+) for chunking API calls. |
| `collections` | `defaultdict`, `Counter`, `deque`, `namedtuple`. |
| `concurrent.futures` | `ThreadPoolExecutor` + `as_completed` — parallel boto3 calls. |
| `tempfile` | `TemporaryDirectory`, `NamedTemporaryFile`. |
| `signal` | Handle `SIGTERM` so a long-running janitor exits cleanly in a container. |
| `sys` | `sys.exit(code)`, `sys.argv`, `sys.stderr`. |
| `re` | Compile once at module level if it's in a loop. |
| `unittest.mock` | `patch`, `MagicMock`, `call` — plus `pytest` fixtures, `tmp_path`, `monkeypatch`, `parametrize`. |

---

## 6. Gotchas that cost real time

1. **Mutable default arguments.** `def f(items=[])` shares one list across every call. Use
   `items: list[str] | None = None` and build inside.
2. **Bare `except:`** swallows `KeyboardInterrupt` and `SystemExit` too. Catch `Exception` at
   minimum, the specific error ideally.
3. **Late-binding closures.** Lambdas in a loop all see the *final* value. Bind it:
   `lambda x, n=n: ...`.
4. **Mutating a list while iterating it** silently skips elements. Iterate a copy or build a new list.
5. **`is` on ints/strings** appears to work because of interning, then fails on the value that
   wasn't interned. Use `==`.
6. **`assert` for validation** vanishes under `-O`. Raise a real exception instead.
7. **`datetime.utcnow()`** — naive, deprecated. Always `datetime.now(UTC)`.
8. **Shadowing builtins** (`list`, `dict`, `id`, `type`, `input`) — legal, and it breaks the next
   line that needed the real one.
9. **`x.strip("abc")`** strips *characters*, not the substring `"abc"`. For prefixes/suffixes use
   `removeprefix`/`removesuffix` (3.9+).
10. **Relative paths in a script that gets run from anywhere.** Anchor on `Path(__file__).parent`
    or require absolute paths in the CLI.

---

## 7. Drill order

If you're using this as a memory list rather than a reference, the payoff order is roughly:

1. `with`, `yield`, `for/else`, `try/except/else/finally`, `raise ... from`
2. Comprehensions + `enumerate` / `zip(strict=True)` / `any` / `all` / `sorted(key=)`
3. `pathlib` and `dataclasses` — they replace most hand-written glue
4. The typing column, because `mypy --strict` is in the done bar
5. `match`/`case` and `:=` — the two that make recent Python look like recent Python
