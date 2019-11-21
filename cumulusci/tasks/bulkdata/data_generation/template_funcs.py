import random
from datetime import date
from .data_gen_exceptions import DataGenError

from faker import Faker

fake = Faker()


def choose(context, *values, on=None):
    if not on:
        on = context.counter_generator.get_value(context.current_table_name)
    return values[(on - 1) % len(values)]


def random_number(context, min, max):
    return random.randint(min, max)


def weighted_choice(choices):
    options = list(choices.keys())
    if any(choices.values()):
        weights = [int(weight.strip("%")) for weight in choices.values()]
    else:
        weights = None
    return random.choices(options, weights, k=1)[0]


def random_choice(context, *choices, **kwargs):
    if hasattr(choices, "keys"):
        return weighted_choice(choices)
    elif kwargs:
        return weighted_choice(kwargs)
    else:
        return random.choice(choices)


def parse_date(d):
    if isinstance(d, str):
        try:
            return date.fromisoformat(d)
        except Exception:
            pass


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
    "random_number": random_number,
    "random_choice": random_choice,
    "date_between": date_between,
    "reference": reference,
    "counter": counter,
}
