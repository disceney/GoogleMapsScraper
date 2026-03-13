from __future__ import annotations

import re

from playwright.sync_api import Page

from utils import normalize_text


def get_locator_text (page: Page, selectors: list[str]) -> str :
	for selector in selectors :
		try :
			locator = page.locator(selector = selector).first
			if locator.count() == 0 :
				continue
			if not locator.is_visible(timeout = 1000) :
				continue
			text: str = normalize_text(text = locator.inner_text(timeout = 3000))
			if text :
				return text
		except Exception :
			continue
	return ""


def get_locator_attribute (page: Page, selectors: list[str], attribute_name: str) -> str :
	for selector in selectors :
		try :
			locator = page.locator(selector = selector).first
			if locator.count() == 0 :
				continue
			value: str | None = locator.get_attribute(name = attribute_name, timeout = 3000)
			if value :
				return value.strip()
		except Exception :
			continue
	return ""


def check_permanently_closed (page: Page) -> bool :
	detail_panel = page.locator(selector = 'div[role="main"]').first
	
	try :
		if detail_panel.count() == 0 :
			return False
	except Exception :
		return False
	
	closed_texts: list[str] = [
		"Définitivement fermé",
		"Permanently closed",
	]
	
	for closed_text in closed_texts :
		try :
			locator = detail_panel.get_by_text(text = closed_text, exact = True).first
			if locator.count() > 0 and locator.is_visible(timeout = 1000) :
				return True
		except Exception :
			continue
	
	return False


def extract_business_name (page: Page) -> str :
	return get_locator_text(
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


def extract_category_value (page: Page) -> str :
	return get_locator_text(
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


def category_matches (found_category: str, searched_category: str) -> bool :
	if not found_category :
		return True
	
	a: str = found_category.casefold().strip()
	b: str = searched_category.casefold().strip()
	
	return a == b or a in b or b in a


def extract_address (page: Page) -> str :
	return get_locator_text(
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


def extract_phone (page: Page) -> str :
	return get_locator_text(
		page = page,
		selectors = [
			'button[data-item-id^="phone:tel:"] .Io6YTe',
			'button[aria-label^="Numéro de téléphone"] .Io6YTe',
			'button[data-tooltip="Copier le numéro de téléphone"] .Io6YTe',
			'button[data-item-id^="phone:tel:"] div[class^="Io6YTe"]',
			'button[data-item-id^="phone:tel:"]',
		],
	)


def extract_website (page: Page) -> str :
	return get_locator_attribute(
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
			selectors = [".F7nice", ".fontBodyMedium.dmRWX"],
		),
		get_locator_attribute(
			page = page,
			selectors = [
				'span[role="img"][aria-label*="étoiles"]',
				'span[role="img"][aria-label*="stars"]',
			],
			attribute_name = "aria-label",
		),
	]
	
	for candidate in candidates :
		match = re.search(pattern = r"(\d[,.]\d)", string = candidate)
		if match is not None :
			return match.group(1).replace(",", ".")
	
	return ""


def extract_business_details (page: Page, category_name: str) -> dict[str, str] :
	if check_permanently_closed(page = page) :
		raise ValueError("Business is permanently closed.")
	
	business_name: str = extract_business_name(page = page)
	category_value: str = extract_category_value(page = page)
	
	if not category_matches(found_category = category_value, searched_category = category_name) :
		raise ValueError(f"Category mismatch: found '{category_value}', expected '{category_name}'.")
	
	address: str = extract_address(page = page)
	phone: str = extract_phone(page = page)
	website: str = extract_website(page = page)
	
	rating_block_text: str = get_locator_text(
		page = page,
		selectors = ["div.F7nice", "div.LBgpqf", ".LBgpqf .F7nice", ".LBgpqf", ".F7nice"],
	)
	
	rating: str = extract_rating(page = page)
	review_count: str = extract_review_count(text = rating_block_text)
	google_maps_url: str = page.url
	
	return {
		"business_name" : business_name,
		"category_name" : category_value or category_name,
		"address" : address,
		"phone" : phone,
		"website" : website,
		"rating" : rating,
		"review_count" : review_count,
		"email" : "",
		"google_maps_url" : google_maps_url,
	}
