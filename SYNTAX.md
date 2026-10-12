# Python syntax — the sigil decoder

Companion to [KEYWORDS.md](KEYWORDS.md). That file answers *"what is this name for."* This one
answers *"what is this punctuation doing here,"* which is the actual reason modern Python reads
like line noise.

**The root cause, stated once:** Python has about eight symbols and reuses each of them for three
to five unrelated jobs. The symbol never tells you the job — **position does.** `*` in a `def`
means one thing, `*` in a call means the reverse, `*` in a list literal means a third thing, and a
bare `*` with nothing after it means a fourth. Once you read position first and symbol second, the
density stops being noise.

Examples are from this track's own code — mostly
[`exercises/02-health-checker`](exercises/02-health-checker), which runs Python 3.14. Version
markers are noted where they matter; assume 3.12+ is available.

---

## 0. Lookup index — Ctrl-F the symbol

| Symbol | Jobs it has | Section |
|---|---|---|
| `:` | annotation · dict pair · slice · start-a-block · walrus half | [1](#1--the-colon) |
| `*` | varargs · unpack-into-call · unpack-into-literal · keyword-only marker · multiply | [2](#2--and--star-and-double-star) |
| `**` | kwargs · unpack-dict-into-call · dict merge in literal · power | [2](#2--and--star-and-double-star) |
| `/` | positional-only marker · true division · `Path` join | [3](#3--the-slash) |
| `->` | return annotation | [4](#4---and-the-annotation-grammar) |
| `=` | assignment · keyword argument · default value · f-string debug | [5](#5-the-four-equals) |
| `:=` | walrus, assign inside an expression | [5](#5-the-four-equals) |
| `@` | decorator · matrix multiply | [6](#6--decorators) |
| `\|` | union type · bitwise or · dict merge | [7](#7--pipe) |
| `[]` | subscript · list literal · generic parameter · slice | [8](#8--brackets-and-generics) |
| `...` | `Ellipsis` — stub body · "required" sentinel · numpy axis | [9](#9--ellipsis) |
| `_` | unused · private hint · `__dunder__` · name mangling · digit separator | [10](#10-_-underscores) |
| `!r` `:>10,` `=` | f-string conversion & format spec | [11](#11-f-strings) |
| `Annotated[...]` | type + runtime metadata (typer, pydantic) | [12](#12-annotated--the-one-that-looks-worst) |

---

## 1. `:` — the colon

Five jobs. Position decides.

```python
def run_one_check(check: Check, retries: int) -> CheckResult:   # 1. annotation, 2. block opener
    config = {"timeout": 5, "retries": 2}                       # 3. dict key:value
    recent = results[1:4]                                       # 4. slice start:stop
    while chunk := fh.read(8192):                               # 5. half of :=
        ...
```

**Annotation vs dict is the one that trips people.** `{"a": 1}` is a dict. `a: int` is an
annotation. `{"a": int}` is a dict whose value happens to be a type. Inside a `class` body,
`name: str` is an annotation and produces **no attribute** — that's why pydantic models look empty:

```python
class Check(BaseModel):
    name: str          # annotation only. Check.name does not exist as a class attribute.
    url: HttpUrl       # pydantic reads these out of __annotations__ to build the validator.
```

Spacing convention (PEP 8, and `ruff` will enforce it): always `name: str`, never `name : str`.
In a slice, no spaces: `a[1:4]`.

---

## 2. `*` and `**` — star and double-star

The single biggest source of "what does this even do." **Five positions, five meanings.**

### In a `def` — *collect* leftovers

```python
def f(a, *args, **kwargs): ...
#        ^^^^^ collects extra positionals into a tuple
#               ^^^^^^^^ collects extra keywords into a dict
```

```python
def _make(name: str, url, **kwargs):          # tests/conftest.py
    return Check(**kwargs, name=name, url=url)
```

`kwargs` is an ordinary `dict`. `args` is an ordinary `tuple`. The stars exist only at the
boundary; inside the body they're plain variables.

### In a call — *spread* a collection

The exact mirror image. Same symbols, opposite direction.

```python
Check(**kwargs, name=name, url=url)    # dict  -> keyword arguments
run_all_checks(*[check1, check2], 3)   # list  -> positional arguments
print(*urls, sep="\n")                 # each item becomes its own argument
```

You can use several in one call: `f(*a, *b, **c, **d)`.

### In a literal — *splat* into a new container

```python
[*head, *tail]           # concatenate lists
{*a, *b}                 # union of sets
{**defaults, **overrides}   # merge dicts; later key wins
(*args, extra)           # build a tuple
```

`{**a, **b}` tolerates duplicate keys (last wins). `dict(**a, **b)` raises `TypeError` on a
duplicate. Different code path, same-looking syntax.

### Bare `*` in a `def` — *keyword-only marker*

Nothing collects. It's a fence: everything after it **must** be passed by name.

```python
def sweep(root: Path, *, apply: bool = False, protect: list[str] | None = None): ...

sweep(path, True)          # TypeError - positional not allowed past the fence
sweep(path, apply=True)    # correct
```

Use this for boolean flags. `sweep(path, True, False)` at a call site is unreadable; forcing
`apply=True` fixes it permanently. This is why `@dataclass(frozen=True, slots=True)` and
`zip(a, b, strict=True)` can't be called positionally.

### In destructuring — *absorb the middle*

```python
first, *rest = urls          # rest is a list, possibly empty
*most, last = urls
head, *_, tail = urls        # discard the middle
```

Exactly one star per target list. The starred name always binds a `list`, even from a tuple.

### And the boring one

`3 * 4` multiply, `2 ** 8` power. Context makes these unambiguous, but it's why you can't grep
for stars.

---

## 3. `/` — the slash

```python
4 / 2                       # true division -> 2.0 (always float; // is floor division)
Path("/srv") / "app.log"    # pathlib join, via __truediv__
def __call__(self, /, *args, **kwargs): ...   # positional-only marker (3.8+)
```

The third one looks like a typo and isn't. Everything **before** `/` can only be passed
positionally — so those names are freed up for callers to use as keywords. That's precisely why
`unittest.mock` declares `def __call__(self, /, *args, **kwargs)`: it lets you mock a function
that has a parameter genuinely named `self` without a collision.

Mnemonic: `def f(a, /, b, *, c)` → `a` positional-only, `b` either, `c` keyword-only. The markers
split the signature into three zones, left to right.

---

## 4. `->` and the annotation grammar

`->` introduces the **return** annotation. That's its only job.

```python
def run_all_checks(checks: list[Check], retries: int) -> list[CheckResult]: ...
def get_logger(name: str = "healthchecker") -> logging.Logger: ...
def main() -> None: ...        # mypy --strict requires this even when it returns nothing
```

Three things that surprise people:

1. **Annotations are not enforced.** Nothing checks them at runtime. `run_one_check("nonsense", "x")`
   runs. Enforcement comes from `mypy`/`ruff` (static) or pydantic (which reads the annotations and
   builds real validators).
2. **They are ordinary expressions**, evaluated at `def` time in ≤3.13. A reference to a
   class defined later raises `NameError` at import — which is what
   `from __future__ import annotations` (top of `conftest.py`, `test_cli.py`) fixes by storing them
   as strings instead. Python 3.14 makes them lazy by default (PEP 649), so this import is becoming
   unnecessary.
3. **PEP 8 spacing flips with annotations.** Annotated defaults get spaces, bare ones don't:

```python
def f(timeout: int = 5): ...   # annotated  -> spaces around =
def f(timeout=5): ...          # bare       -> no spaces
f(timeout=5)                   # call site  -> never spaces
```

---

## 5. The four equals

| Form | Meaning |
|---|---|
| `x = 5` | assignment (statement — cannot appear inside an expression) |
| `f(timeout=5)` | keyword argument at a **call** site |
| `def f(timeout=5)` | default value in a **definition** |
| `x == 5` | equality comparison |
| `x := 5` | **walrus** — assign *and* evaluate to the value |

The walrus exists so you can bind and test in one breath:

```python
while chunk := fh.read(8192):        # read, bind, test truthiness
    process(chunk)

if (found := [r for r in results if not r.passed]):
    logger.error("checks failed", extra={"fields": {"count": len(found)}})
```

`=` vs `==` in an `if` is a syntax error in Python, not a silent bug — one thing it got right
that C didn't.

---

## 6. `@` decorators

`@thing` above a `def` means: define the function, pass it to `thing`, rebind the name to whatever
comes back. These two are identical:

```python
@app.command()
def main(): ...

def main(): ...
main = app.command()(main)
```

**Three shapes, and the difference matters:**

```python
@patch("healthchecker.check.requests.get")        # called with args -> returns the decorator
def test_a(mock_get): ...

@pytest.fixture                                   # bare -> is the decorator itself
def now(): ...

@pytest.fixture()                                 # also legal here; pytest accepts both
def now(): ...
```

Getting this wrong fails confusingly: a bare `@patch` (no arguments) passes your *function* as the
`target` string and blows up somewhere unrelated.

**Stacking applies bottom-up.** The decorator closest to `def` runs first, so it is the
*innermost* wrapper — and with `@patch`, the *first* parameter:

```python
@patch("healthchecker.check.logger")      # applied second -> second parameter
@patch("healthchecker.check.requests.get")  # applied first -> first parameter
def test_each_retry_emits_one_warning(mock_get, mock_logger, init_check):
    ...                                   # pytest fixtures come after all injected mocks
```

Decorators you'll meet on this track: `@dataclass`, `@property`, `@staticmethod`, `@classmethod`,
`@functools.cache`, `@functools.wraps`, `@contextlib.contextmanager`, `@pytest.fixture`,
`@pytest.mark.parametrize`, `@pytest.mark.xfail`, `@patch`, `@app.command()`, `@overload`.

(`@` between two operands is matrix multiplication — `a @ b`. numpy only; you will never type it here.)

---

## 7. `|` pipe

```python
expect_value: str | int | None = None    # union type (models.py)
flags = READ | WRITE                     # bitwise or
merged = defaults | overrides            # dict merge, 3.9+
```

`X | None` replaces `Optional[X]`. Prefer it. At runtime the union form in annotations needs 3.10+,
or `from __future__ import annotations` on older versions.

`|` in a `case` pattern means "or": `case 200 | 201 | 204:`.

---

## 8. `[]` brackets and generics

```python
urls[0]                      # subscript
[1, 2, 3]                    # list literal
list[str]                    # generic parameter - a type, not a lookup
dict[str, list[Path]]        # nested generics
results[1:4]                 # slice
```

`list[str]` looks like indexing because it **is** — `type.__getitem__` returns a
`types.GenericAlias`. Since 3.9 you use builtins directly; `typing.List` is dead weight.

### Slicing, completely

```python
xs[start:stop]        # stop is exclusive
xs[start:stop:step]
xs[:3]  xs[3:]  xs[:] # omit either end; xs[:] copies a list
xs[::-1]              # reverse
xs[-1]                # last; xs[-2:] last two
xs[1:99]              # never IndexError - slices clamp, unlike xs[99]
```

That last line is worth internalising: indexing raises, slicing doesn't.

### Type-parameter syntax (3.12+)

```python
type Findings = dict[str, list[Path]]     # type alias statement
def first[T](items: list[T]) -> T: ...    # generic function, no TypeVar boilerplate
class Pool[T]: ...
```

---

## 9. `...` Ellipsis

A real singleton object named `Ellipsis`, not "to be continued."

```python
def run_one_check(check: Check) -> CheckResult: ...   # stub body, same as `pass`
class Runner(Protocol):
    def run(self) -> None: ...                        # protocol/stub declaration
x: int = ...                                          # "required" sentinel (pydantic, typer)
```

Typer and pydantic both use `...` to mean **required, no default**. That's a library convention,
not language semantics.

---

## 10. `_` underscores

| Form | Meaning |
|---|---|
| `_` | "I don't need this." `for _ in range(3)`, `head, *_, tail` |
| `_name` | private by convention. Nothing enforces it; linters respect it |
| `__name` | **name mangling** inside a class: becomes `_ClassName__name` |
| `__name__` | dunder — a language/protocol hook. Never invent your own |
| `1_000_000` | digit separator, purely cosmetic |
| `case _:` | wildcard pattern (the default arm) |

Name mangling is the one that bites: `self.__lock` inside `ScriptedGet` is physically stored as
`self._ScriptedGet__lock`, so subclasses can't accidentally clobber it — and `getattr(obj, "__lock")`
fails.

---

## 11. f-strings

```python
f"Retry calling to {url} {count} times"     # check.py:18
f"{value!r}"                                # !r repr, !s str, !a ascii
f"{count=}"                                 # -> "count=3"  (debug specifier, 3.8+)
f"{ratio:.2%}"                              # -> "94.00%"
f"{size:>10,}"                              # right-align width 10, thousands separators
f"{size:<10}" f"{size:^10}"                 # left, centre
f"{name:{width}}"                           # nested - width comes from a variable
f"{ts:%Y-%m-%d}"                            # datetime format spec
f"{{literal braces}}"                       # double them to escape
rf"\d+{suffix}"                             # combine prefixes: raw + f
```

`f"{count=}"` is the one to steal — it prints name *and* value, which is most of what a debug
`print` was for.

Format spec shape: `[[fill]align][sign][#][0][width][grouping][.precision][type]`. You will only
ever use `width`, `,`, `.Nf`, and `%`.

**String prefixes:** `f` format, `r` raw (regex, Windows paths), `b` bytes, `rb`/`br` both, `u`
legacy no-op. No `rf` vs `fr` distinction — order is free.

**Implicit concatenation** — adjacent literals merge with no operator. Useful, and a classic
missing-comma bug:

```python
msg = ("check failed: "        # fine, deliberate
       "retries exhausted")

urls = ["http://a"  "http://b"]   # BUG: one string "http://ahttp://b", missing comma
```

Since 3.12 f-strings may reuse the outer quote type and nest freely: `f"{d["key"]}"`.

---

## 12. `Annotated[...]` — the one that looks worst

This is the syntax that makes `cli.py` hard to read, so here it is taken apart.

```python
check: Annotated[str | None, typer.Option(help="Check single endpoint.")] = None
#^^^^                                                                        ^^^^
# parameter name                                                        default value
#      ^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#      the actual type        runtime metadata, ignored by type checkers
```

`Annotated[T, m1, m2, ...]` means **"the type is `T`; additionally, carry this metadata."** Type
checkers read only `T`. Libraries read the rest at runtime via
`typing.get_type_hints(fn, include_extras=True)`. It's a way to attach library config to a
parameter without inventing new syntax — which is why every modern library uses it and why
signatures got so wide.

### Your `cli.py`, decoded — and a real trap in it

```python
# current code
check: Annotated[str | None, typer.Option(default="--check", help="...")]
```

`typer.Option`'s signature is `Option(default=..., *param_decls, **kwargs)`. So `default="--check"`
fills the **default-value** slot, not a flag name. It works anyway — but only because Typer
notices it's inside `Annotated` and shuffles it over:

> `typer/utils.py:141-149` — "When used in `Annotated`, `Option` just takes option names as
> positional arguments. In this case, the `default` attribute is actually meant to be the first
> item of `param_decls`."

So Typer silently rewrites `default="--check"` into `param_decls=("--check",)`. Relying on that is
a trap, because the *same spelling* in the older non-`Annotated` style really does set the default
value to the literal string `"--check"`. Write flag names positionally:

```python
check: Annotated[str | None, typer.Option("--check", "-c", help="...")] = None
config_file: Annotated[Path, typer.Option("--config", "-f", help="Path to config file")]
```

Second consequence, visible in `--help` right now: neither parameter has `= <default>`, so Typer
marks **both** `[required]`. `check` is typed `str | None` but `None` is unreachable — add
`= None` if a bare `healthcheck --config x.yaml` should run every check.

### The same pattern in pydantic

```python
class Check(BaseModel):
    name: str = Field()                       # models.py
    expect_status: int = Field(gt=199, lt=600)
```

`Field()` in the default slot looks like "default = a Field object." It isn't — pydantic
special-cases `FieldInfo` and treats it as *configuration*. A bare `Field()` with no `default=`
leaves the field **required**. The `Annotated` spelling says the same thing without the
misdirection, and is what pydantic's own docs now prefer:

```python
expect_status: Annotated[int, Field(gt=199, lt=600)]
```

---

## 13. `with` — context managers

`with` is `try/finally` with the cleanup written once, inside the object. Any object with
`__enter__`/`__exit__` works.

```python
with ThreadPoolExecutor(max_workers=10) as pool:      # check.py - pool.shutdown() guaranteed
    ...

with patch("healthchecker.check.requests.get") as mock_get:   # patch undone on exit
    ...

with self._lock:              # threading.Lock - acquire/release, no `as` needed
    ...
```

`as` binds whatever `__enter__` returns — which is **not** always the object. `open()` returns the
file; `patch()` returns the `MagicMock`; `Lock` returns `None`, which is why you never write
`with lock as l`.

**Several at once** — comma-separated, left to right, each unwound in reverse:

```python
with open(src) as fin, open(dst, "w") as fout:
    ...

with (                                     # parenthesised form, 3.10+, for long lists
    patch("healthchecker.check.requests.get") as mock_get,
    patch("healthchecker.check.logger") as mock_logger,
):
    ...
```

Write your own with `@contextlib.contextmanager` — everything before `yield` is `__enter__`,
everything after is `__exit__`:

```python
@contextmanager
def timed(label: str):
    start = time.monotonic()
    try:
        yield                                  # the `with` body runs here
    finally:
        logger.info("done", extra={"fields": {"label": label, "s": time.monotonic() - start}})
```

---

## 14. Comprehensions

One grammar, four containers. The trailing `for`/`if` read top-to-bottom as if they were nested
loops.

```python
[r for r in results if not r.passed]              # list
{p.suffix for p in paths}                         # set
{c.name: c.url for c in checks}                   # dict
sum(p.stat().st_size for p in paths)              # generator - nothing materialised
```

**`if` has two legal positions and they do different things:**

```python
[x for x in xs if x > 0]            # filter - short list, skips items
[x if x > 0 else 0 for x in xs]     # ternary - same length, transforms items
```

The first drops elements; the second keeps all of them. Both read "if x > 0".

**Nesting order is the confusing part** — the `for` clauses go in the same order you'd write nested
loops, but the output expression sits at the *front*:

```python
[(c.name, header) for c in checks for header in (c.expect_headers or {})]
#                 ^^^^^^^^^^^^^^^ outer loop    ^^^^^^^^^^^^^^^^^^^^^^^ inner loop
```

Equivalent to:

```python
out = []
for c in checks:
    for header in (c.expect_headers or {}):
        out.append((c.name, header))
```

A generator expression is the same syntax with no brackets, and it's what you want for anything
large — `any(not r.passed for r in results)` stops at the first failure and builds no list.

---

## 15. Expression forms worth naming

```python
"pass" if result.passed else "fail"     # ternary: value-first, unlike every other language
199 < status < 600                      # chained comparison - evaluates status once
name in {"a", "b"}                      # membership; O(1) on set/dict, O(n) on list
x is None                               # identity - only for None/True/False/sentinels
not results                             # empty list/dict/str/0/None are all falsy
count or 1                              # returns an operand, not a bool
lambda c: c.name                        # one-expression function, e.g. sorted(key=...)
```

`sorted(checks, key=lambda c: c.name, reverse=True)` is the canonical `lambda` use. If it needs a
statement, it needs a `def`.

---

## 16. Class-body syntax you'll read constantly

```python
@dataclass
class CheckResult:
    name: str                        # required field
    passed: bool = False             # default
    error: str | None = None
```

`@dataclass` reads `__annotations__` and writes `__init__`, `__repr__`, `__eq__` for you. Ordering
rule: fields without defaults must come before fields with them. Mutable defaults need
`field(default_factory=list)` — a plain `= []` raises at class-creation time, because the
[mutable-default bug](KEYWORDS.md#6-gotchas-that-cost-real-time) would otherwise be shared across
instances.

`CheckResult(check.name, passed=False)` — positional then keyword, the normal call grammar.

Useful modifiers: `@dataclass(frozen=True, slots=True, kw_only=True)`.

---

## 17. Generators

```python
def read_lines(path: Path) -> Iterator[str]:
    with path.open() as fh:
        for line in fh:
            yield line.rstrip("\n")     # any `yield` makes the whole function a generator

yield from other_iterable               # delegate
```

Calling a generator function runs **no code** — it returns a generator. The body advances only on
each `next()`. That's the whole trick for files bigger than RAM, and the reason a generator can be
consumed exactly once.

---

## 18. Syntax-level gotchas

1. **A one-element tuple needs the comma.** `(5)` is the int 5; `(5,)` is a tuple. This is why
   `except (ValueError):` and `except ValueError:` are the same thing.
2. **Trailing commas are legal and good** in multi-line collections and calls — they keep diffs to
   one line. Not after `*args`/`**kwargs` in a call, and never in a one-element tuple you didn't
   mean.
3. **Missing comma in a list of strings silently concatenates** (see §11).
4. **Mutable default arguments** are evaluated once at `def` time. `def f(items=[])` shares one
   list forever. Use `items: list[str] | None = None`.
5. **Bare `except:`** catches `KeyboardInterrupt` and `SystemExit`. `check.py:16` uses
   `except Exception` — correct, though catching `requests.RequestException` would be tighter and
   wouldn't mask the `KeyError` kind of bug.
6. **Indentation is syntax.** Mixing tabs and spaces is a `TabError`. Four spaces, always.
7. **`return` inside `finally`** discards any in-flight exception. Never do it.
8. **Annotations don't validate.** `-> CheckResult` will not stop you returning `None`.
9. **`is` is not `==`.** `x is 200` appears to work via int interning, then fails past 256.
10. **`global`/`nonlocal` are declarations, not assignments** — they go at the top of the function
    and change what a later `=` binds.

---

## 19. Reading drill

Decode these three, out loud, without scrolling up. Each one is from this workspace.

```python
# 1
config_file: Annotated[Path, typer.Option(default="--config", help="Path to config file")]

# 2
future_to_check = {pool.submit(run_one_check, check, retries, t): check for check in checks}

# 3
assert all(c.kwargs["timeout"] == 5 for c in mock_get.call_args_list)
```

<details>
<summary>Answers</summary>

1. Parameter `config_file`, type `Path`, carrying a `typer.Option` as runtime metadata. The
   `default=` is Typer's re-interpreted flag name (§12) — should be positional. No `=` after the
   `]`, so it's **required**.
2. A **dict comprehension** whose *key* is the return of `pool.submit(...)` (a `Future`) and whose
   *value* is the `check`. The colon separates key from value; the `for` is the loop. Idiom:
   remember which input produced which future, so `as_completed` can map back.
3. `all(...)` over a **generator expression** — no list built, short-circuits on the first `False`.
   `c.kwargs` is the `_Call` tuple's keyword half. Reads: "every recorded call passed
   `timeout=5`."

</details>

---

## 20. Drill order

If you're using this as a memory list:

1. `*`/`**` in all five positions (§2) — highest payoff by a wide margin
2. `Annotated[...]` (§12) — unlocks reading typer, pydantic, and FastAPI signatures
3. Decorator shapes and stacking order (§6) — unlocks the test suite
4. Comprehension grammar, especially `if` in both positions (§14)
5. f-string format specs (§11) and `with` multi-manager forms (§13)
6. The bare `*` keyword-only fence (§2) — then start using it in your own signatures
