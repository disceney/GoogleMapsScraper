from __future__ import annotations

from playwright.sync_api import Page

from browser import (
	click_result_card,
	get_result_card_summaries,
	get_result_cards,
	read_detail_panel_name,
	scroll_feed_once,
	wait_for_detail_panel_change,
)
from config import COMPANIES_FILE
from csv_helpers import (
	append_company_to_csv,
	build_company_keys,
	ensure_companies_csv,
	load_existing_company_keys,
)
from extractors import extract_business_details
from utils import (
	log_info,
	log_success,
	log_warning,
)


def build_company_row (details: dict[str, str], summary: dict[str, str], category_name: str) -> dict[str, str] :
	return {
		"business_name" : details.get("business_name") or summary.get("business_name", ""),
		"category_name" : details.get("category_name") or category_name,
		"address" : details.get("address", ""),
		"phone" : details.get("phone", ""),
		"website" : details.get("website", ""),
		"rating" : details.get("rating", ""),
		"review_count" : details.get("review_count", ""),
		"email" : details.get("email", ""),
		"google_maps_url" : details.get("google_maps_url", ""),
	}


def process_visible_results (page: Page, category_name: str, saved_keys: set[str], processed_urls: set[str]) -> int :
	summaries: list[dict[str, str]] = get_result_card_summaries(page = page)
	new_saved_count: int = 0
	
	for summary in summaries :
		result_url: str = summary.get("result_url", "")
		business_name: str = summary.get("business_name", "")
		
		if result_url and result_url in processed_urls :
			continue
		
		summary_keys: list[str] = build_company_keys(
			business_name = business_name,
			google_maps_url = result_url,
		)
		
		if summary_keys and any(k in saved_keys for k in summary_keys) :
			if result_url :
				processed_urls.add(result_url)
			continue
		
		log_info(message = f"Processing: {business_name}")
		
		previous_panel_name: str = read_detail_panel_name(page = page)
		
		clicked: bool = click_result_card(
			page = page,
			target_result_url = result_url,
			target_business_name = business_name,
		)
		
		if not clicked :
			log_warning(message = f"Could not click result: {business_name}")
			if result_url :
				processed_urls.add(result_url)
			continue
		
		if result_url :
			processed_urls.add(result_url)
		
		wait_for_detail_panel_change(
			page = page,
			previous_name = previous_panel_name,
			expected_name = business_name,
		)
		
		try :
			details: dict[str, str] = extract_business_details(
				page = page,
				category_name = category_name,
			)
		except ValueError as error :
			log_warning(message = f"Skipped '{business_name}': {error}")
			continue
		except Exception as error :
			log_warning(message = f"Failed to extract details for '{business_name}': {error}")
			continue
		
		row: dict[str, str] = build_company_row(
			details = details,
			summary = summary,
			category_name = category_name,
		)
		
		row_keys: list[str] = build_company_keys(
			business_name = row.get("business_name", ""),
			google_maps_url = row.get("google_maps_url", ""),
			category_name = row.get("category_name", ""),
			address = row.get("address", ""),
		)
		
		if not row_keys :
			log_warning(message = f"Skipped empty row for '{business_name}'")
			continue
		
		if any(k in saved_keys for k in row_keys) :
			log_warning(message = f"Duplicate skipped: {row.get('business_name', business_name)}")
			continue
		
		append_company_to_csv(file_path = COMPANIES_FILE, company = row)
		saved_keys.update(row_keys)
		saved_keys.update(summary_keys)
		
		new_saved_count += 1
		log_success(message = f"Saved: {row['business_name']}")
	
	return new_saved_count


def scrape_results_progressively (page: Page, category_name: str) -> int :
	ensure_companies_csv(file_path = COMPANIES_FILE)
	saved_keys: set[str] = load_existing_company_keys(file_path = COMPANIES_FILE)
	processed_urls: set[str] = set()
	
	rounds_without_progress: int = 0
	previous_total_cards: int = 0
	total_saved_now: int = 0
	
	while True :
		current_total_cards: int = get_result_cards(page).count()
		log_info(message = f"Visible results count: {current_total_cards}")
		
		saved_this_round: int = process_visible_results(
			page = page,
			category_name = category_name,
			saved_keys = saved_keys,
			processed_urls = processed_urls,
		)
		
		total_saved_now += saved_this_round
		
		before_scroll_top, after_scroll_top, after_scroll_height = scroll_feed_once(page = page)
		new_total_cards: int = get_result_cards(page).count()
		
		has_new_cards: bool = new_total_cards > current_total_cards
		has_new_saved: bool = saved_this_round > 0
		has_scrolled: bool = after_scroll_top > before_scroll_top
		has_card_growth: bool = new_total_cards > previous_total_cards
		
		log_info(
			message = (
				f"Cards={new_total_cards} | Saved this round={saved_this_round} | "
				f"scrollTop: {before_scroll_top}->{after_scroll_top} | "
				f"scrollHeight={after_scroll_height}"
			)
		)
		
		if has_new_cards or has_new_saved or has_scrolled or has_card_growth :
			rounds_without_progress = 0
		else :
			rounds_without_progress += 1
		
		previous_total_cards = new_total_cards
		
		if rounds_without_progress >= 3 :
			log_success(message = "End of results reached or no more progress detected.")
			break
	
	return total_saved_now
