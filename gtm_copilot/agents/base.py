"""Abstract Base Agent definition."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all specialized AI agents."""

    def __init__(self, name: str):
        """Initialize base agent with an identifying name.

        Args:
            name: Identifier for the agent.
        """
        self.name = name

    @abstractmethod
    async def run(self, input: Any) -> Any:
        """Execute the agent workflow for the given input.

        Args:
            input: Domain-specific input payload.

        Returns:
            Domain-specific output payload.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"
