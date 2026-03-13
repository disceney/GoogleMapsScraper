from __future__ import annotations

from typing import Any
from urllib.parse import quote

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from browser import launch_maps_context
from config import CATEGORIES_FILE, COMPANIES_FILE, GOOGLE_MAPS_SEARCH_URL
from csv_helpers import ensure_companies_csv, load_categories
from scraper import scrape_results_progressively
from utils import (
	human_sleep_before_parse,
	log_error,
	log_info,
	log_success,
	log_warning,
)


def build_google_maps_url (category_name: str, description: str) -> str :
	query: str = quote(string = f"{category_name} - {description}")
	return GOOGLE_MAPS_SEARCH_URL.format(query = query)


def prompt_description () -> str :
	description: str = input("Enter a French description (postal code, etc.): ").strip()
	return description


def run_category_search (playwright: Any, category_name: str, description: str) -> int :
	google_maps_url: str = build_google_maps_url(
		category_name = category_name,
		description = description,
	)
	
	context = launch_maps_context(playwright = playwright)
	
	try :
		page = context.new_page()
		
		log_info(message = f"Opening Google Maps for: {category_name} - {description}")
		page.goto(url = google_maps_url, wait_until = "domcontentloaded")
		
		try :
			page.wait_for_selector(selector = 'div[role="feed"]', timeout = 30000)
		except PlaywrightTimeoutError :
			log_warning(message = f"Results panel did not load for: {category_name}")
			return 0
		
		human_sleep_before_parse()
		
		total_saved_now: int = scrape_results_progressively(
			page = page,
			category_name = category_name,
		)
		
		log_success(message = f"Finished category '{category_name}' with {total_saved_now} new companies.")
		return total_saved_now
	
	finally :
		log_info(message = f"Closing browser for category: {category_name}")
		context.close()


def main () -> None :
	try :
		categories: list[str] = load_categories(file_path = CATEGORIES_FILE)
	except (FileNotFoundError, ValueError) as error :
		log_error(message = f"{error}")
		return
	
	description: str = prompt_description()
	ensure_companies_csv(file_path = COMPANIES_FILE)
	
	grand_total_saved: int = 0
	
	with sync_playwright() as playwright :
		for index, category_name in enumerate(categories, start = 1) :
			log_info(message = f"Category {index}/{len(categories)}: {category_name}")
			
			try :
				saved_count: int = run_category_search(
					playwright = playwright,
					category_name = category_name,
					description = description,
				)
				grand_total_saved += saved_count
			except Exception as error :
				log_error(message = f"Failed for category '{category_name}': {error}")
	
	log_success(message = f"Done: {grand_total_saved} new companies saved to '{COMPANIES_FILE}'.")


if __name__ == "__main__" :
	main()
