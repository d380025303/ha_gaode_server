cache_dict = {}


def set_cache(k, v):
    cache_dict[k] = v


def get_cache(k):
    if k in cache_dict:
        return cache_dict[k]
    return None
