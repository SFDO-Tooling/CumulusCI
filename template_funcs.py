from datetime import datetime
import os


def parentField(context, name):
    return context.parent.obj.fields[name]


def otherField(context, name):
    return context.objs.fields[name]


def ancestorId(context, sobject_name):
    return context.ancestor_field(sobject_name, "id")


def ancestorField(context, sobject_name, field_name):
    current_context = context
    while current_context and current_context.obj:
        if current_context.obj.sftype == sobject_name:
            return current_context.obj.fields[field_name]
        else:
            current_context = current_context.parent
    raise Exception(f"Ancestor not found {sobject_name}")


def var(context, varname):
    # TODO: use task variables not environment variables
    #       in final version
    return os.environ[varname]


def today(context):
    return datetime.now().date()


def choose(context, index, *values):
    return values[(index - 1) % len(values)]


template_funcs = {
    "ancestorId": ancestorId,
    "ancestorField": ancestorField,
    "today": today,
    "otherField": otherField,
    "parentField": parentField,
    "var": var,
    "int": lambda context, number: int(number),
    "choose": choose,
}
