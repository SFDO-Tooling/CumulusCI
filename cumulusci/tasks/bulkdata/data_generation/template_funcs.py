from random import randint, choice, choices as randchoices
from datetime import date


from faker import Faker

fake = Faker()


def choose(context, *values, on=None):
    if not on:
        on = context.counter_generator.get_value(context.sobject_name)
    return values[(on - 1) % len(values)]


def random_number(context, min, max):
    return randint(min, max)


def weighted_choice(choices):
    options = list(choices.keys())
    if any(choices.values()):
        weights = [int(weight.strip("%")) for weight in choices.values()]
    else:
        weights = None
    return randchoices(options, weights, k=1)[0]


def random_choice(context, *choices, **kwargs):
    if hasattr(choices, "keys"):
        return weighted_choice(choices)
    elif kwargs:
        return weighted_choice(kwargs)
    else:
        return choice(choices)


def parse_date(d):
    if isinstance(d, str):
        try:
            return date.fromisoformat(d)
        except Exception:
            pass


def date_between(context, start_date, end_date):
    start_date = parse_date(start_date) or start_date
    end_date = parse_date(end_date) or end_date
    return fake.date_between(start_date, end_date)


template_funcs = {
    "int": lambda context, number: int(number),
    "choose": choose,
    "random_number": random_number,
    "random_choice": random_choice,
    "date_between": date_between,
}
