from abc import ABC, abstractmethod
from typing import Dict


class PEPProvider(ABC):
    @abstractmethod
    def screen(self, subject: Dict) -> Dict:
        """Return normalized PEP screening response."""
