"""
LinkedIn people search via Selenium.

Searches for people by name and returns a list of profile URLs
found on the search results page.
"""

import re
import urllib.parse
import logging
from time import sleep
from dataclasses import dataclass, field
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .objects import Scraper

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/search/results/people/"


@dataclass
class SearchResult:
    """A single person result from LinkedIn search."""
    name: str = None
    linkedin_url: str = None
    headline: str = None


class PersonSearch(Scraper):
    """Search LinkedIn for people by name and return profile URLs."""

    def __init__(self, driver, close_on_complete=False):
        super().__init__()
        self.driver = driver
        self.WAIT_FOR_ELEMENT_TIMEOUT = 10

    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        Search LinkedIn for people matching the query.

        Args:
            query: Search term (e.g. a person's full name)
            limit: Maximum number of results to return

        Returns:
            List of SearchResult with name, linkedin_url, and headline
        """
        if not self.is_signed_in():
            logger.error("Not signed in to LinkedIn")
            return []

        encoded = urllib.parse.quote(query)
        url = f"{SEARCH_URL}?keywords={encoded}&origin=GLOBAL_SEARCH_HEADER"
        self.driver.get(url)

        sleep(3)
        self.scroll_to_half()
        sleep(2)

        results = []

        try:
            # Find all profile links in search results
            # LinkedIn wraps each result in a <span> or <a> with href containing /in/
            links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/in/"]')

            seen_urls = set()
            for link in links:
                href = link.get_attribute("href")
                if not href or "/in/" not in href:
                    continue

                # Normalize URL: take only the /in/username/ part
                match = re.search(r'(https://www\.linkedin\.com/in/[^/?]+)', href)
                if not match:
                    continue

                profile_url = match.group(1) + "/"
                if profile_url in seen_urls:
                    continue
                seen_urls.add(profile_url)

                # Try to extract name and headline from the link's context
                name = None
                headline = None
                try:
                    # The link text or its parent often contains the name
                    name_text = link.text.strip()
                    if name_text and len(name_text) > 1:
                        name = name_text
                except Exception:
                    pass

                try:
                    # Headline is usually in a sibling or nearby element
                    parent = link.find_element(By.XPATH, "./ancestor::li")
                    subtitle = parent.find_element(
                        By.CSS_SELECTOR,
                        'div.entity-result__primary-subtitle'
                    )
                    headline = subtitle.text.strip() if subtitle else None
                except (NoSuchElementException, Exception):
                    pass

                results.append(SearchResult(
                    name=name,
                    linkedin_url=profile_url,
                    headline=headline,
                ))

                if len(results) >= limit:
                    break

        except TimeoutException:
            logger.warning(f"Timeout loading search results for: {query}")
        except Exception as e:
            logger.warning(f"Error parsing search results for '{query}': {e}")

        logger.info(f"Search '{query}': found {len(results)} results")
        return results
