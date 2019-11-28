import random
from datetime import date, datetime
from .data_gen_exceptions import DataGenError

from faker import Faker

fake = Faker()

# It might make more sense to use context vars for context handling when
# Python 3.6 is out of the support matrix.


def lazy(func):
    func.lazy = True
    return func


def choose(context, *values, on=None):
    if not on:
        on = context.counter_generator.get_value(context.current_table_name)
    return values[(on - 1) % len(values)]


def random_number(context, min, max):
    return random.randint(min, max)


def parse_weight_str(context, weight_value):
    weight_str = weight_value.render(context)
    if not weight_str.endswith("%"):
        raise ValueError(f"random_choice weight should end in '%': {weight_str}")
    return int(weight_str.rstrip("%"))


def weighted_choice(choices):
    weights = [weight for weight, value in choices]
    options = [value for weight, value in choices]
    return random.choices(options, weights, k=1)[0]


@lazy
def random_choice(context, *choices):
    if not choices:
        raise ValueError("No choices supplied!")

    if getattr(choices[0], "function_name", None) == "choice":
        choices = [choice.render(context) for choice in choices]
        return weighted_choice(choices).render(context)
    else:
        return random.choice(choices).render(context)


@lazy
def choice_wrapper(context, probability, pick):
    probability = parse_weight_str(context, probability)
    return probability, pick


def parse_date(d):
    if isinstance(d, str):
        try:
            return date.fromisoformat(d)
        except Exception:
            pass


def date_(context, *, year, month, day):
    return date(year, month, day)


def datetime_(context, *, year, month, day, hour=0, minute=0, second=0, microsecond=0):
    return datetime(year, month, day, hour, minute, second, microsecond)


def date_between(context, start_date, end_date):
    start_date = parse_date(start_date) or start_date
    end_date = parse_date(end_date) or end_date
    try:
        return fake.date_between(start_date, end_date)
    except ValueError as e:
        if "empty range" not in str(e):
            raise
    # swallow empty range errors per Python conventions


def reference(context, x):
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


def counter(context, name):
    return context.counter_generator.get_value(name)


template_funcs = {
    "int": lambda context, number: int(number),
    "choose": choose,
    "choice": choice_wrapper,
    "random_number": random_number,
    "random_choice": random_choice,
    "date_between": date_between,
    "reference": reference,
    "counter": counter,
    "date": date_,
    "datetime": datetime_,
}
