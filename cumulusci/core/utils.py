def import_class(path):
    components = path.split('.')
    module = components[:-1]
    module = '.'.join(module)
    mod = __import__(module, fromlist=[components[-1]])
    return getattr(mod, components[-1])
