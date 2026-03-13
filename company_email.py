from __future__ import annotations

from typing import Any

from playwright.sync_api import sync_playwright

from browser import launch_browser_context
from config import COMPANIES_FILE
from csv_helpers import load_companies, save_companies
from email_helpers import extract_email_from_website
from utils import (
	human_sleep_before_parse,
	log_error,
	log_info,
	log_success,
	log_warning,
)

PAGE_LOAD_TIMEOUT: int = 15000


def visit_website_and_extract_email (context: Any, website_url: str) -> str :
	page = context.new_page()
	
	try :
		page.goto(url = website_url, wait_until = "domcontentloaded", timeout = PAGE_LOAD_TIMEOUT)
		human_sleep_before_parse()
		email: str = extract_email_from_website(page = page)
		return email
	except Exception as error :
		log_warning(message = f"Could not load '{website_url}': {error}")
		return ""
	finally :
		page.close()


def process_companies (companies: list[dict[str, str]], context: Any) -> int :
	updated_count: int = 0
	total: int = len(companies)
	
	for index, company in enumerate(companies, start = 1) :
		business_name: str = company.get("business_name", "")
		website: str = company.get("website", "").strip()
		existing_email: str = company.get("email", "").strip()
		
		if existing_email :
			continue
		
		if not website :
			continue
		
		log_info(message = f"[{index}/{total}] Visiting website for: {business_name}")
		
		email: str = visit_website_and_extract_email(
			context = context,
			website_url = website,
		)
		
		if email :
			company["email"] = email
			updated_count += 1
			log_success(message = f"Found email for '{business_name}': {email}")
		else :
			log_warning(message = f"No email found for '{business_name}'")
	
	return updated_count


def main () -> None :
	try :
		companies: list[dict[str, str]] = load_companies(file_path = COMPANIES_FILE)
	except FileNotFoundError as error :
		log_error(message = f"{error}")
		return
	
	without_email: int = sum(
		1 for c in companies
		if not c.get("email", "").strip() and c.get("website", "").strip()
	)
	
	if without_email == 0 :
		log_success(message = "All companies with a website already have an email. Nothing to do.")
		return
	
	log_info(message = f"Found {without_email} companies without email (with a website). Starting extraction.")
	
	with sync_playwright() as playwright :
		context = launch_browser_context(playwright = playwright, headless = False)
		
		try :
			updated_count: int = process_companies(
				companies = companies,
				context = context,
			)
		finally :
			context.close()
	
	if updated_count > 0 :
		save_companies(file_path = COMPANIES_FILE, companies = companies)
	
	log_success(message = f"Done: {updated_count} emails added to '{COMPANIES_FILE}'.")


if __name__ == "__main__" :
	main()
