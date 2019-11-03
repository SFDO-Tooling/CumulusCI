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


def now(context):
    return datetime.now()


template_funcs = {
    "ancestorId": ancestorId,
    "ancestorField": ancestorField,
    "now": now,
    "otherField": otherField,
    "parentField": parentField,
    "var": var,
    "int": lambda context, number: int(number),
}
