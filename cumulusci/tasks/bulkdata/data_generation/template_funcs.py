import random
from datetime import date, datetime
import dateutil

from .data_gen_exceptions import DataGenError
from typing import Callable, Any, Optional, Union, List, Tuple

from faker import Faker

fake = Faker()

# It might make more sense to use context vars for context handling when
# Python 3.6 is out of the support matrix.


def lazy(func: Any) -> Callable:
    """A lazy function is one that expects its arguments to be unparsed"""
    func.lazy = True
    return func


def random_number(context, min: int, max: int) -> int:
    """Pick a random number between min and max like Python's randint."""
    return random.randint(min, max)


def parse_weight_str(context, weight_value) -> int:
    """For constructs like:

    - choice:
        probability: 60%
        pick: Closed Won

    Convert the 60% to just 60.
    """
    weight_str = weight_value.render(context)
    if isinstance(weight_str, str):
        weight_str = weight_str.rstrip("%")
    return int(weight_str)


def weighted_choice(choices: List[Tuple[int, object]]):
    """Selects from choices based on their weights"""
    weights = [weight for weight, value in choices]
    options = [value for weight, value in choices]
    return random.choices(options, weights, k=1)[0]


@lazy
def random_choice(context, *choices):
    """Template helper for random choices.

    Supports structures like this:

    random_choice:
        - a
        - b
        - <<c>>

    Or like this:

    random_choice:
        - choice:
            pick: A
            probability: 50%
        - choice:
            pick: A
            probability: 50%

    Probabilities are really just weights and don't need to
    add up to 100.

    Pick-items can have arbitrary internal complexity.

    Pick-items are lazily evaluated.
    """
    if not choices:
        raise ValueError("No choices supplied!")

    if getattr(choices[0], "function_name", None) == "choice":
        choices = [choice.render(context) for choice in choices]
        rc = weighted_choice(choices)
    else:
        rc = random.choice(choices)
    if hasattr(rc, "render"):
        rc = rc.render(context)
    return rc


@lazy
def choice_wrapper(context, pick, probability=None, when=None):
    """Supports the choice: sub-items used in `random_choice`z or `if`"""
    if probability:
        probability = parse_weight_str(context, probability)
    if not (probability or when):
        raise ValueError("Choice should have `probabily` or `choice` property set")
    return probability or when, pick


def parse_date(d: object) -> Optional[datetime]:
    try:
        return dateutil.parser.parse(d)
    except Exception:
        pass


def date_(
    context, *, year: Union[str, int], month: Union[str, int], day: Union[str, int]
):
    """A YAML-embeddable function to construct a date from strings or integers"""
    return date(year, month, day)


def datetime_(context, *, year, month, day, hour=0, minute=0, second=0, microsecond=0):
    """A YAML-embeddable function to construct a datetime from strings or integers"""
    return datetime(year, month, day, hour, minute, second, microsecond)


def date_between(context, start_date, end_date):
    """A YAML-embeddable function to pick a date between two ranges"""
    start_date = parse_date(start_date) or start_date
    end_date = parse_date(end_date) or end_date
    try:
        return fake.date_between(start_date, end_date)
    except ValueError as e:
        if "empty range" not in str(e):
            raise
    # swallow empty range errors per Python conventions


def reference(context, x):
    """YAML-embeddable function to Reference another object."""
    if hasattr(x, "id"):  # reference to an object with an id
        target = x
    elif isinstance(x, str):  # name of an object
        obj = context.field_vars()[x]
        if not getattr(obj, "id"):
            raise DataGenError(f"Reference to incorrect object type {obj}", None, None)
        target = obj
    else:
        raise DataGenError(
            f"Can't get reference to object of type {type(x)}: {x}", None, None
        )

    return target


@lazy
def if_(context, *choices):
    """Template helper for conditional choices.

    Supports structures like this:

    if:
        - choice:
            when: <<something>>
            pick: A
        - choice:
            when: <<something>>
            pick: B

    Pick-items can have arbitrary internal complexity.

    Pick-items are lazily evaluated.
    """
    if not choices:
        raise ValueError("No choices supplied!")

    choices = [choice.render(context) for choice in choices]
    print(
        list(
            (cond.render(context), choice)
            for cond, choice in choices
            if cond.render(context)
        )
    )
    true_choices = (choice for cond, choice in choices if cond.render(context))
    rc = next(true_choices, None)
    if hasattr(rc, "render"):
        rc = rc.render(context)
    return rc


template_funcs = {
    "int": lambda context, number: int(number),
    "choice": choice_wrapper,
    "random_number": random_number,
    "random_choice": random_choice,
    "date_between": date_between,
    "reference": reference,
    "date": date_,
    "datetime": datetime_,
    "if": if_,
}
