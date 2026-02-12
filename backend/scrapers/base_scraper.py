from abc import ABC, abstractmethod
from typing import List, Dict

class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, city: str) -> List[Dict]:
        """
        Scrape jobs for a specific city.
        Returns a list of dictionaries containing job details.
        """
        pass
