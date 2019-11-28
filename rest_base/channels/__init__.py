try:
    import channels
except ImportError as e:
    raise ImportError(
        'channels must be installed to use rest_base.consumers. Try `pip install django-rest-base[channels]`.'
    ) from e
