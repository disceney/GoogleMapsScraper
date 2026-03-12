from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Locator, Page, sync_playwright, TimeoutError as PlaywrightTimeoutError

from utils import (
	human_sleep_after_click,
	human_sleep_before_parse,
	log_error,
	log_info,
	log_success,
	log_warning,
	normalize_text,
)

CATEGORIES_FILE: str = "categories.csv"
COMPANIES_FILE: str = "companies.csv"
CHROME_AUTOMATION_PROFILE_DIR: str = str(Path.cwd() / "chrome-profile")
CHROME_EXECUTABLE_PATH: str = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
GOOGLE_MAPS_SEARCH_URL: str = "https://www.google.com/maps/search/{query}"

COMPANY_FIELDNAMES: list[str] = [
	"business_name",
	"category_name",
	"postal_code",
	"address",
	"phone",
	"website",
	"rating",
	"review_count",
	"email",
	"google_maps_url",
]


def is_valid_french_postal_code (postal_code: str) -> bool :
	cleaned_postal_code: str = postal_code.strip()
	return re.fullmatch(pattern = r"\d{2}|\d{5}", string = cleaned_postal_code) is not None


def load_categories (file_path: str) -> list[str] :
	path: Path = Path(file_path)
	
	if not path.exists() :
		raise FileNotFoundError(f"Categories file not found: {file_path}")
	
	categories: list[str] = []
	seen: set[str] = set()
	
	with open(file = file_path, mode = "r", encoding = "utf-8", newline = "") as file_handle :
		reader = csv.DictReader(f = file_handle)
		
		if reader.fieldnames and "category_name" in reader.fieldnames :
			for row in reader :
				category_name: str = normalize_text(text = (row.get("category_name") or ""))
				
				if category_name and category_name not in seen :
					seen.add(category_name)
					categories.append(category_name)
		else :
			file_handle.seek(0)
			raw_reader = csv.reader(file_handle)
			
			for row in raw_reader :
				if not row :
					continue
				
				category_name = normalize_text(text = row[0])
				
				if not category_name :
					continue
				
				if category_name.casefold() in {"category_name", "category", "name", "business_name"} :
					continue
				
				if category_name not in seen :
					seen.add(category_name)
					categories.append(category_name)
	
	if not categories :
		raise ValueError("Categories CSV is empty.")
	
	return categories


def prompt_postal_code () -> str :
	while True :
		postal_code: str = input("📮 Enter a French postal code: ").strip()
		
		if is_valid_french_postal_code(postal_code = postal_code) :
			log_success(message = f"✅ Postal code accepted: {postal_code}")
			return postal_code
		
		log_error(message = "❌ Invalid postal code. Expected exactly 5 digits.")


def ensure_companies_csv (file_path: str) -> None :
	path: Path = Path(file_path)
	
	if path.exists() :
		return
	
	with open(file = file_path, mode = "w", encoding = "utf-8", newline = "") as file_handle :
		writer = csv.DictWriter(
			f = file_handle,
			fieldnames = COMPANY_FIELDNAMES,
		)
		writer.writeheader()


def append_company_to_csv (file_path: str, company: dict[str, str]) -> None :
	with open(file = file_path, mode = "a", encoding = "utf-8", newline = "") as file_handle :
		writer = csv.DictWriter(
			f = file_handle,
			fieldnames = COMPANY_FIELDNAMES,
		)
		writer.writerow(company)


def build_company_key_from_values (business_name: str, google_maps_url: str, ) -> str :
	normalized_name: str = normalize_text(text = business_name).casefold()
	normalized_url: str = google_maps_url.strip()
	
	if normalized_url :
		return f"url::{normalized_url}"
	
	if normalized_name :
		return f"name::{normalized_name}"
	
	return ""


def load_existing_company_keys (file_path: str) -> set[str] :
	path: Path = Path(file_path)
	existing_keys: set[str] = set()
	
	if not path.exists() :
		return existing_keys
	
	with open(file = file_path, mode = "r", encoding = "utf-8", newline = "") as file_handle :
		reader = csv.DictReader(f = file_handle)
		
		for row in reader :
			row_key: str = build_company_key_from_values(
				business_name = (row.get("business_name") or ""),
				google_maps_url = (row.get("google_maps_url") or ""),
			)
			if row_key :
				existing_keys.add(row_key)
	
	return existing_keys


def launch_maps_context (playwright: Any) :
	return playwright.chromium.launch_persistent_context(
		user_data_dir = CHROME_AUTOMATION_PROFILE_DIR,
		executable_path = CHROME_EXECUTABLE_PATH,
		headless = False,
		no_viewport = True,
	)


def wait_for_results_panel (page: Page) -> None :
	page.wait_for_selector(selector = 'div[role="feed"]', timeout = 30000)


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
		"result_url" : result_url
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


def wait_for_business_details (page: Page) -> None :
	detail_selectors: list[str] = [
		"h1.DUwDvf",
		"h1.lfPIob",
		'button[data-item-id="address"]',
		'button[data-item-id^="phone:tel:"]',
		'a[data-item-id="authority"]',
	]
	
	deadline: float = time.time() + 30.0
	
	while time.time() < deadline :
		for selector in detail_selectors :
			locator = page.locator(selector = selector).first
			
			try :
				if locator.count() > 0 and locator.is_visible() :
					time.sleep(2.0)
					return
			except Exception :
				continue
		
		time.sleep(1.0)
	
	raise PlaywrightTimeoutError("Business details panel did not load in time.")


def get_locator_text (page: Page, selectors: list[str]) -> str :
	for selector in selectors :
		locator = page.locator(selector = selector).first
		
		try :
			if locator.count() == 0 :
				continue
			
			text: str = normalize_text(text = locator.inner_text(timeout = 3000))
			
			if text :
				return text
		except Exception :
			continue
	
	return ""


def get_locator_attribute (page: Page, selectors: list[str], attribute_name: str) -> str :
	for selector in selectors :
		locator = page.locator(selector = selector).first
		
		try :
			if locator.count() == 0 :
				continue
			
			value: str | None = locator.get_attribute(name = attribute_name, timeout = 3000)
			
			if value :
				return value.strip()
		except Exception :
			continue
	
	return ""


def extract_review_count (text: str) -> str :
	match = re.search(pattern = r"\(([\d\s.,]+)\)", string = text)
	
	if match is not None :
		return normalize_text(text = match.group(1))
	
	match = re.search(pattern = r"(\d[\d\s.,]*)\s+avis", string = text, flags = re.IGNORECASE)
	
	if match is not None :
		return normalize_text(text = match.group(1))
	
	match = re.search(pattern = r"(\d[\d\s.,]*)\s+reviews", string = text, flags = re.IGNORECASE)
	
	if match is not None :
		return normalize_text(text = match.group(1))
	
	return ""


def extract_rating (page: Page) -> str :
	candidates: list[str] = [
		get_locator_text(
			page = page,
			selectors = [
				".F7nice",
				".fontBodyMedium.dmRWX",
			],
		),
		get_locator_attribute(
			page = page,
			selectors = ['span[role="img"][aria-label*="étoiles"]', 'span[role="img"][aria-label*="stars"]'],
			attribute_name = "aria-label",
		),
	]
	
	for candidate in candidates :
		match = re.search(pattern = r"(\d[,.]\d)", string = candidate)
		
		if match is not None :
			return match.group(1).replace(",", ".")
	
	return ""


def extract_email (page: Page) -> str :
	mailto_href: str = get_locator_attribute(
		page = page,
		selectors = ['a[href^="mailto:"]'],
		attribute_name = "href",
	)
	
	if mailto_href.startswith("mailto:") :
		return mailto_href.replace("mailto:", "", 1).strip()
	
	try :
		body_text: str = page.locator(selector = "body").inner_text(timeout = 3000)
		match = re.search(
			pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
			string = body_text,
		)
		if match is not None :
			return match.group(0)
	except Exception :
		pass
	
	return ""


def extract_business_details (page: Page, category_name: str, postal_code: str) -> dict[str, str] :
	business_name: str = get_locator_text(
		page = page,
		selectors = [
			'h1[class^="DUwDvf "]',
			'h1[class="DUwDvf lfPIob"]',
			"h1.DUwDvf.lfPIob",
			"h1.DUwDvf",
			"h1.lfPIob",
			"h1",
		],
	)
	
	category_value: str = get_locator_text(
		page = page,
		selectors = [
			'.fontBodyMedium button[jsaction*=".category"]',
			'.fontBodyMedium button[class^="DkEaL"]',
			'.fontBodyMedium button[class="DkEaL "]',
			'.fontBodyMedium button[class="DkEaL"]',
			'button[jsaction*=".category"]',
			'button[class^="DkEaL"]',
			'button[class="DkEaL "]',
			'button[class="DkEaL"]',
		],
	)
	
	address: str = get_locator_text(
		page = page,
		selectors = [
			'button[data-item-id="address"] .Io6YTe',
			'button[data-tooltip="Copier l\'adresse"] .Io6YTe',
			'button[data-item-id="address"] div[class^="Io6YTe"]',
			'button[data-tooltip="Copier l\'adresse"] div[class^="Io6YTe"]',
			'div[class^="Io6YTe"][class*="fontBodyMedium"]',
			'button[data-item-id="address"]',
			'button[data-tooltip="Copier l\'adresse"]',
		],
	)
	
	phone: str = get_locator_text(
		page = page,
		selectors = [
			'button[data-item-id^="phone:tel:"] .Io6YTe',
			'button[aria-label^="Numéro de téléphone"] .Io6YTe',
			'button[data-tooltip="Copier le numéro de téléphone"] .Io6YTe',
			'button[data-item-id^="phone:tel:"] div[class^="Io6YTe"]',
			'button[data-item-id^="phone:tel:"]',
		],
	)
	
	website: str = get_locator_attribute(
		page = page,
		selectors = [
			'a[data-item-id="authority"]',
			'a[aria-label^="Site Web:"]',
			'a[data-tooltip="Accéder au site Web"]',
			'a[class^="CsEnBe"][data-item-id="authority"]',
			'a[data-item-id="services"]',
			'a[class^="CsEnBe"][data-item-id="services"]',
			'a[data-tooltip="Ouvrir le lien vers les services"]',
		],
		attribute_name = "href",
	)
	
	rating_block_text: str = get_locator_text(
		page = page,
		selectors = [
			"div.F7nice",
			"div.LBgpqf",
			".LBgpqf .F7nice",
			".LBgpqf",
			".F7nice"
		],
	)
	
	rating: str = extract_rating(page = page)
	review_count: str = extract_review_count(text = rating_block_text)
	email: str = extract_email(page = page)
	google_maps_url: str = page.url
	
	return {
		"business_name" : business_name,
		"category_name" : category_value or category_name,
		"postal_code" : postal_code,
		"address" : address,
		"phone" : phone,
		"website" : website,
		"rating" : rating,
		"review_count" : review_count,
		"email" : email,
		"google_maps_url" : google_maps_url,
	}


def build_company_row (details: dict[str, str], summary: dict[str, str], category_name: str, postal_code: str, ) -> dict[str, str] :
	business_name: str = details.get("business_name") or summary.get("business_name", "")
	address: str = details.get("address") or summary.get("address_hint", "")
	phone: str = details.get("phone") or summary.get("phone_hint", "")
	website: str = details.get("website") or summary.get("website_hint", "")
	rating: str = details.get("rating") or summary.get("rating_hint", "")
	review_count: str = details.get("review_count") or summary.get("review_count_hint", "")
	email: str = details.get("email", "")
	google_maps_url: str = details.get("google_maps_url") or summary.get("result_url", "")
	
	return {
		"business_name" : business_name,
		"category_name" : details.get("category_name") or category_name,
		"postal_code" : postal_code,
		"address" : address,
		"phone" : phone,
		"website" : website,
		"rating" : rating,
		"review_count" : review_count,
		"email" : email,
		"google_maps_url" : google_maps_url,
	}


def process_visible_results (page: Page, category_name: str, postal_code: str, saved_keys: set[str], ) -> int :
	summaries: list[dict[str, str]] = get_result_card_summaries(page = page)
	new_saved_count: int = 0
	
	for summary in summaries :
		summary_key: str = build_company_key_from_values(
			business_name = summary.get("business_name", ""),
			google_maps_url = summary.get("result_url", ""),
		)
		
		if summary_key and summary_key in saved_keys :
			continue
		
		business_name: str = summary.get("business_name", "")
		log_info(message = f"📍 Processing: {business_name}")
		
		clicked: bool = click_result_card(
			page = page,
			target_result_url = summary.get("result_url", ""),
			target_business_name = business_name,
		)
		
		if not clicked :
			log_warning(message = f"⚠️ Could not click result: {business_name}")
			continue
		
		try :
			wait_for_business_details(page = page)
		except Exception as error :
			log_warning(message = f"⚠️ Details did not load for '{business_name}': {error}")
			continue
		
		try :
			details: dict[str, str] = extract_business_details(
				page = page,
				category_name = category_name,
				postal_code = postal_code,
			)
		except Exception as error :
			log_warning(message = f"⚠️ Failed to extract details for '{business_name}': {error}")
			continue
		
		row: dict[str, str] = build_company_row(
			details = details,
			summary = summary,
			category_name = category_name,
			postal_code = postal_code,
		)
		
		row_key: str = build_company_key_from_values(
			business_name = row.get("business_name", ""),
			google_maps_url = row.get("google_maps_url", ""),
		)
		
		if not row_key :
			log_warning(message = f"⚠️ Skipped empty row for '{business_name}'")
			continue
		
		if row_key in saved_keys :
			log_warning(message = f"⚠️ Duplicate skipped: {row.get('business_name', business_name)}")
			continue
		
		append_company_to_csv(file_path = COMPANIES_FILE, company = row)
		saved_keys.add(row_key)
		
		if summary_key :
			saved_keys.add(summary_key)
		
		new_saved_count += 1
		log_success(message = f"✅ Saved: {row['business_name']}")
	
	return new_saved_count


def scroll_feed_once (page: Page) -> tuple[int, int, int] :
	feed = get_results_feed(page)
	feed_handle = feed.element_handle()
	
	if feed_handle is None :
		raise RuntimeError("Unable to access results feed element.")
	
	before_state: dict[str, int] = page.evaluate(
		expression = """
        (element) => {
            return {
                scrollTop: element.scrollTop,
                scrollHeight: element.scrollHeight,
                clientHeight: element.clientHeight
            };
        }
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
        (element) => {
            return {
                scrollTop: element.scrollTop,
                scrollHeight: element.scrollHeight,
                clientHeight: element.clientHeight
            };
        }
        """,
		arg = feed_handle,
	)
	
	return (
		before_state["scrollTop"],
		after_state["scrollTop"],
		after_state["scrollHeight"],
	)


def scrape_results_progressively (page: Page, category_name: str, postal_code: str) -> int :
	ensure_companies_csv(file_path = COMPANIES_FILE)
	saved_keys: set[str] = load_existing_company_keys(file_path = COMPANIES_FILE)
	
	rounds_without_progress: int = 0
	previous_total_cards: int = 0
	total_saved_now: int = 0
	
	while True :
		current_total_cards: int = get_result_cards(page).count()
		log_info(message = f"🔎 Visible results count: {current_total_cards}")
		
		saved_this_round: int = process_visible_results(
			page = page,
			category_name = category_name,
			postal_code = postal_code,
			saved_keys = saved_keys,
		)
		
		total_saved_now += saved_this_round
		
		before_scroll_top, after_scroll_top, after_scroll_height = scroll_feed_once(page = page)
		new_total_cards: int = get_result_cards(page).count()
		
		has_new_cards: bool = new_total_cards > current_total_cards
		has_new_saved: bool = saved_this_round > 0
		has_scrolled: bool = after_scroll_top > before_scroll_top
		has_card_growth_since_last_round: bool = new_total_cards > previous_total_cards
		
		log_info(
			message = (
				f"📊 Cards={new_total_cards} | Saved this round={saved_this_round} | "
				f"scrollTop: {before_scroll_top}->{after_scroll_top} | "
				f"scrollHeight={after_scroll_height}"
			)
		)
		
		if has_new_cards or has_new_saved or has_scrolled or has_card_growth_since_last_round :
			rounds_without_progress = 0
		else :
			rounds_without_progress += 1
		
		previous_total_cards = new_total_cards
		
		if rounds_without_progress >= 3 :
			log_success(message = "✅ End of results reached or no more progress detected")
			break
	
	return total_saved_now


def run_category_search (playwright: Any, category_name: str, postal_code: str) -> int :
	google_maps_url: str = build_google_maps_url(
		category_name = category_name,
		postal_code = postal_code,
	)
	
	context = launch_maps_context(playwright = playwright)
	
	try :
		page = context.new_page()
		
		log_info(message = f"🗺️ Opening Google Maps for: {category_name} - {postal_code}")
		page.goto(url = google_maps_url, wait_until = "domcontentloaded")
		
		try :
			wait_for_results_panel(page = page)
		except PlaywrightTimeoutError :
			log_warning(message = f"⚠️ Google Maps results panel did not load for: {category_name}")
			return 0
		
		human_sleep_before_parse()
		
		total_saved_now: int = scrape_results_progressively(
			page = page,
			category_name = category_name,
			postal_code = postal_code,
		)
		
		log_success(
			message = f"✅ Finished category '{category_name}' with {total_saved_now} new companies"
		)
		return total_saved_now
	
	finally :
		log_info(message = f"🔒 Closing browser for category: {category_name}")
		context.close()


def main () -> None :
	try :
		categories: list[str] = load_categories(file_path = CATEGORIES_FILE)
	except (FileNotFoundError, ValueError) as error :
		log_error(message = f"❌ {error}")
		return
	
	postal_code: str = prompt_postal_code()
	ensure_companies_csv(file_path = COMPANIES_FILE)
	
	grand_total_saved: int = 0
	
	with sync_playwright() as playwright :
		for index, category_name in enumerate(categories, start = 1) :
			log_info(message = f"📂 Category {index} / {len(categories)} : {category_name}")
			
			try :
				saved_count: int = run_category_search(
					playwright = playwright,
					category_name = category_name,
					postal_code = postal_code,
				)
				grand_total_saved += saved_count
			except Exception as error :
				log_error(message = f"❌ Failed for category '{category_name}': {error}")
	
	log_success(
		message = f"🎉 Done: {grand_total_saved} new companies saved to '{COMPANIES_FILE}'"
	)


if __name__ == "__main__" :
	main()
