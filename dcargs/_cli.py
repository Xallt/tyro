import argparse
from typing import Callable, Optional, Sequence, TypeVar

import argparse_color_formatter

from . import _calling, _parsers

T = TypeVar("T")


def parse(
    f: Callable[..., T],
    *,
    description: Optional[str] = None,
    args: Optional[Sequence[str]] = None,
    default_instance: Optional[T] = None,
) -> T:  # pragma: no cover
    """Deprecated alias for `dcargs.cli()`."""
    # import warnings
    #
    # warnings.warn(
    #     "`dcargs.parse()` has been renamed `dcargs.cli()`. It will be removed"
    #     " soon.",
    #     DeprecationWarning,
    #     stacklevel=2,
    # )
    return cli(f, description=description, args=args, default_instance=default_instance)


def cli(
    f: Callable[..., T],
    *,
    prog: Optional[str] = None,
    description: Optional[str] = None,
    args: Optional[Sequence[str]] = None,
    default_instance: Optional[T] = None,
    avoid_subparsers: bool = False,
) -> T:
    """Call `f(...)`, with arguments populated from an automatically generated CLI
    interface.

    `f` should have type-annotated inputs, and can be a function or class. Note that if
    `f` is a class, `dcargs.cli()` returns an instance.

    The parser is generated by populating helptext from docstrings and types from
    annotations; a broad range of core type annotations are supported...
        - Types natively accepted by `argparse`: str, int, float, pathlib.Path, etc.
        - Default values for optional parameters.
        - Booleans, which are automatically converted to flags when provided a default
          value.
        - Enums (via `enum.Enum`).
        - Various annotations from the standard typing library. Some examples:
          - `typing.ClassVar[T]`.
          - `typing.Optional[T]`.
          - `typing.Literal[T]`.
          - `typing.Sequence[T]`.
          - `typing.List[T]`.
          - `typing.Dict[K, V]`.
          - `typing.Tuple`, such as `typing.Tuple[T1, T2, T3]` or
            `typing.Tuple[T, ...]`.
          - `typing.Set[T]`.
          - `typing.Final[T]` and `typing.Annotated[T]`.
          - `typing.Union[T1, T2]`.
          - Various nested combinations of the above: `Optional[Literal[T]]`,
            `Final[Optional[Sequence[T]]]`, etc.
        - Hierarchical structures via nested dataclasses, TypedDict, NamedTuple,
          classes.
          - Simple nesting.
          - Unions over nested structures (subparsers).
          - Optional unions over nested structures (optional subparsers).
        - Generics (including nested generics).

    Args:
        f: Callable.

    Keyword Args:
        prog: The name of the program printed in helptext. Mirrors argument from
            `argparse.ArgumentParser()`.
        description: Description text for the parser, displayed when the --help flag is
            passed in. If not specified, `f`'s docstring is used. Mirrors argument from
            `argparse.ArgumentParser()`.
        args: If set, parse arguments from a sequence of strings instead of the
            commandline. Mirrors argument from `argparse.ArgumentParser.parse_args()`.
        default_instance: An instance of `T` to use for default values; only supported
            if `T` is a dataclass, TypedDict, or NamedTuple. Helpful for merging CLI
            arguments with values loaded from elsewhere. (for example, a config object
            loaded from a yaml file)
        avoid_subparsers: Avoid creating a subparser when defaults are provided for
            unions over nested types. Generates cleaner but less expressive CLIs.

    Returns:
        The output of `f(...)`.
    """

    # Map a callable to the relevant CLI arguments + subparsers.
    parser_definition = _parsers.ParserSpecification.from_callable(
        f,
        description=description,
        parent_classes=set(),  # Used for recursive calls.
        parent_type_from_typevar=None,  # Used for recursive calls.
        default_instance=default_instance,  # Overrides for default values.
        prefix="",  # Used for recursive calls.
        avoid_subparsers=avoid_subparsers,
    )

    # Parse using argparse!
    parser = argparse.ArgumentParser(
        prog=prog, formatter_class=argparse_color_formatter.ColorHelpFormatter
    )
    parser_definition.apply(parser)
    value_from_prefixed_field_name = vars(parser.parse_args(args=args))

    try:
        # Attempt to call `f` using whatever was passed in.
        out, consumed_keywords = _calling.call_from_args(
            f,
            parser_definition,
            default_instance,
            value_from_prefixed_field_name,
            field_name_prefix="",
            avoid_subparsers=avoid_subparsers,
        )
    except _calling.InstantiationError as e:
        # Emulate argparse's error behavior when invalid arguments are passed in.
        parser.print_usage()
        print()
        print(e.args[0])
        raise SystemExit()

    # assert consumed_keywords == value_from_prefixed_field_name.keys()
    return out
