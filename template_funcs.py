def choose(context, *values, on=None):
    if not on:
        on = context.counter_generator.get_value(context.sobject_name)
    return values[(on - 1) % len(values)]


template_funcs = {"int": lambda context, number: int(number), "choose": choose}
