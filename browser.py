from __future__ import annotations

import time
from typing import Any

from playwright.sync_api import Locator, Page

from config import CHROME_AUTOMATION_PROFILE_DIR, CHROME_EXECUTABLE_PATH
from utils import (
	human_sleep_after_click,
	human_sleep_before_parse,
	normalize_text,
)


def launch_maps_context (playwright: Any) :
	return playwright.chromium.launch_persistent_context(
		user_data_dir = CHROME_AUTOMATION_PROFILE_DIR,
		executable_path = CHROME_EXECUTABLE_PATH,
		headless = False,
		no_viewport = True,
	)


def get_results_feed (page: Page) -> Locator :
	locator = page.locator(selector = 'div[role="feed"]').first

	if locator.count() == 0 :
		raise RuntimeError("Results feed not found.")

	return locator


def get_result_cards (page: Page) -> Locator :
	return page.locator(selector = 'div[role="feed"] div[role="article"], div[role="feed"] div.Nv2PK')


def extract_card_summary (card: Locator) -> dict[str, str] :
	business_name: str = ""
	result_url: str = ""

	try :
		business_name = normalize_text(text = card.locator(selector_or_locator = ".qBF1Pd.fontHeadlineSmall").first.inner_text(timeout = 1000))
	except Exception :
		pass

	try :
		result_url = card.locator(selector_or_locator = "a.hfpxzc").first.get_attribute(name = "href") or ""
	except Exception :
		pass

	return {
		"business_name" : business_name,
		"result_url" : result_url,
	}


def get_result_card_summaries (page: Page) -> list[dict[str, str]] :
	cards = get_result_cards(page)
	summaries: list[dict[str, str]] = []
	seen_urls: set[str] = set()
	total_cards: int = cards.count()

	for index in range(total_cards) :
		try :
			card = cards.nth(index)
			summary: dict[str, str] = extract_card_summary(card = card)
			result_url: str = summary.get("result_url", "")

			if result_url and result_url in seen_urls :
				continue

			if result_url :
				seen_urls.add(result_url)

			if summary.get("business_name") or result_url :
				summaries.append(summary)
		except Exception :
			continue

	return summaries


def click_result_card (page: Page, target_result_url: str, target_business_name: str) -> bool :
	cards = get_result_cards(page)
	total_cards: int = cards.count()

	for index in range(total_cards) :
		try :
			card = cards.nth(index)
			summary: dict[str, str] = extract_card_summary(card = card)

			summary_url: str = summary.get("result_url", "")
			summary_name: str = summary.get("business_name", "")

			same_url: bool = bool(target_result_url) and summary_url == target_result_url
			same_name: bool = bool(target_business_name) and summary_name == target_business_name

			if not same_url and not same_name :
				continue

			card.scroll_into_view_if_needed(timeout = 5000)
			human_sleep_before_parse()

			link = card.locator(selector_or_locator = "a.hfpxzc").first
			link.click(timeout = 10000, force = True)

			human_sleep_after_click()
			return True
		except Exception :
			continue

	return False


def read_detail_panel_name (page: Page) -> str :
	for selector in ("h1.DUwDvf", "h1.lfPIob", "h1") :
		try :
			locator = page.locator(selector = selector).first
			if locator.count() > 0 and locator.is_visible() :
				return normalize_text(text = locator.inner_text(timeout = 2000))
		except Exception :
			continue
	return ""


def wait_for_detail_panel_change (page: Page, previous_name: str, expected_name: str) -> None :
	"""
	Wait until the detail panel reflects a NEW business, then wait a bit
	more so that secondary elements (status, rating, category, etc.) finish
	updating too.
	"""
	deadline: float = time.time() + 15.0

	while time.time() < deadline :
		current_name: str = read_detail_panel_name(page = page)

		if expected_name and current_name == expected_name :
			break

		if previous_name and current_name and current_name != previous_name :
			break

		time.sleep(0.5)

	# The h1 has changed, but secondary elements (closed badge, rating,
	# category button, etc.) may still show stale content from the
	# previous business.  Give the DOM time to fully settle.
	time.sleep(2.0)


def scroll_feed_once (page: Page) -> tuple[int, int, int] :
	feed = get_results_feed(page)
	feed_handle = feed.element_handle()

	if feed_handle is None :
		raise RuntimeError("Unable to access results feed element.")

	before_state: dict[str, int] = page.evaluate(
		expression = """
		(element) => ({
			scrollTop: element.scrollTop,
			scrollHeight: element.scrollHeight,
			clientHeight: element.clientHeight
		})
		""",
		arg = feed_handle,
	)

	page.evaluate(
		expression = """
		(element) => {
			element.scrollBy(0, Math.max(1200, Math.floor(element.clientHeight * 0.9)));
		}
		""",
		arg = feed_handle,
	)

	time.sleep(2.5)

	after_state: dict[str, int] = page.evaluate(
		expression = """
		(element) => ({
			scrollTop: element.scrollTop,
			scrollHeight: element.scrollHeight,
			clientHeight: element.clientHeight
		})
		""",
		arg = feed_handle,
	)

	return (
		before_state["scrollTop"],
		after_state["scrollTop"],
		after_state["scrollHeight"],
	)
