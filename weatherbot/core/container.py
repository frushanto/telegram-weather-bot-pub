import inspect
import logging
from contextvars import ContextVar
from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class Container:

    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}

    def register_singleton(self, interface: Type[T], implementation: T) -> None:

        key = interface.__name__
        self._singletons[key] = implementation

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:

        key = interface.__name__
        self._factories[key] = factory

    def register_instance(self, interface: Type[T], instance: T) -> None:

        key = interface.__name__
        self._services[key] = instance

    def get(self, interface: Type[T]) -> T:

        key = interface.__name__

        if key in self._singletons:
            return self._singletons[key]

        if key in self._services:
            return self._services[key]

        if key in self._factories:
            return self._factories[key]()

        try:
            if hasattr(interface, "__init__"):
                sig = inspect.signature(interface.__init__)
                params = [p for name, p in sig.parameters.items() if name != "self"]
                if not params:
                    instance = interface()
                    self._services[key] = instance
                    return instance
        except (TypeError, ValueError) as e:
            logger.debug("Failed to auto-instantiate %s: %s", interface.__name__, e)

        raise ValueError(f"Service {interface.__name__} not registered in container")

    def clear(self) -> None:

        self._services.clear()
        self._singletons.clear()
        self._factories.clear()


_current_container: ContextVar[Container | None] = ContextVar(
    "_current_container", default=None
)


def set_container(container: Container) -> None:

    _current_container.set(container)


def get_container() -> Container:

    container = _current_container.get()
    if container is None:
        raise RuntimeError("Dependency container has not been initialised")
    return container


def reset_container() -> None:

    container = _current_container.get()
    if container is not None:
        container.clear()
    _current_container.set(None)


class ContainerProxy:

    def __getattr__(self, item: str) -> Any:

        return getattr(get_container(), item)

    def __call__(self) -> Container:

        return get_container()


container = ContainerProxy()
