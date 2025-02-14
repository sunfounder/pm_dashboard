def log_error(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            self.log.exception(str(e))
    return wrapper

def merge_dict(dict1, dict2):
    new_dict = dict1.copy()
    for key in dict2:
        if isinstance(dict2[key], dict):
            if key not in dict1:
                dict1[key] = {}
            new_dict[key] = merge_dict(dict1[key], dict2[key])
        elif isinstance(dict2[key], list):
            if key not in dict1:
                new_dict[key] = []
            new_dict[key].extend(dict2[key])
        else:
            new_dict[key] = dict2[key]
    return new_dict
