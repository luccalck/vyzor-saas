from typing import Dict, Type, List

from .base import Connector


class ConnectorRegistry:
    """Registro de conectores disponíveis."""

    def __init__(self) -> None:
        self._registry: Dict[str, Type[Connector]] = {}

    def register(self, key: str, connector_cls: Type[Connector]) -> None:
        self._registry[key] = connector_cls

    def get(self, key: str) -> Type[Connector] | None:
        return self._registry.get(key)

    def list_keys(self) -> List[str]:
        return sorted(self._registry.keys())

    def list_connectors(self) -> List[dict]:
        items = []
        for key, cls in self._registry.items():
            name = getattr(cls, "name", key)
            items.append({"key": key, "name": name})
        return sorted(items, key=lambda x: x["key"])


# Instância global do registry
registry = ConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    return registry