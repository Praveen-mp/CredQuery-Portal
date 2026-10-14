from dbchat.adapters.base import BaseDBAdapter

_REGISTRY: dict[str, type[BaseDBAdapter]] = {}


def register(adapter_cls: type[BaseDBAdapter]) -> type[BaseDBAdapter]:
    """Class decorator. @register on a BaseDBAdapter subclass makes it
    selectable in the UI and buildable by its `key`."""
    _REGISTRY[adapter_cls.key] = adapter_cls
    return adapter_cls


def get_adapter_class(key: str) -> type[BaseDBAdapter]:
    try:
        return _REGISTRY[key]
    except KeyError as exc:
        raise ValueError(
            f"No adapter registered for db_type={key!r}. Available: {list(_REGISTRY)}"
        ) from exc


def available_adapters() -> dict[str, str]:
    """{key: display_name} for every registered adapter — feeds the UI's
    'database type' dropdown."""
    return {key: cls.display_name for key, cls in _REGISTRY.items()}
