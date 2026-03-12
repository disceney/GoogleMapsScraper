import csv
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from utils import (
	human_sleep_after_click,
	human_sleep_before_parse,
	log_error,
	log_info,
	log_success,
	log_warning,
	normalize_text,
)

URL: str = "https://pleper.com/index.php?do=tools&sdo=gmb_categories&go=1&lang=fr&country=66&show_table=1"
OUTPUT_FILE: str = "categories.csv"
MAX_PAGES: int = 39
CHROME_AUTOMATION_PROFILE_DIR: str = str(Path.cwd() / "chrome-profile")
CHROME_EXECUTABLE_PATH: str = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def write_categories_csv (file_path: str, category_names: list[str]) -> None :
	with open(file = file_path, mode = "w", encoding = "utf-8", newline = "") as file_handle :
		writer = csv.DictWriter(
			f = file_handle,
			fieldnames = ["category_name"],
		)
		writer.writeheader()
		
		for category_name in category_names :
			writer.writerow({"category_name" : category_name})


def main () -> None :
	with sync_playwright() as playwright :
		context = playwright.chromium.launch_persistent_context(
			user_data_dir = CHROME_AUTOMATION_PROFILE_DIR,
			executable_path = CHROME_EXECUTABLE_PATH,
			headless = False,
		)
		
		page = context.new_page()
		page.goto(url = URL, wait_until = "domcontentloaded")
		
		table = page.locator(selector = "table.table.table-responsive.table-hover.table-bordered").first
		table.wait_for()
		
		seen: set[str] = set()
		category_names: list[str] = []
		page_index: int = 1
		
		while page_index <= MAX_PAGES :
			human_sleep_before_parse()
			
			log_info(message = f"📖 Parsing page {page_index}/{MAX_PAGES}")
			
			category_links = table.locator(selector_or_locator = "tbody tr td:nth-child(2) a")
			current_names: list[str] = [
				normalize_text(text = text)
				for text in category_links.all_inner_texts()
			]
			
			added_count: int = 0
			for category_name in current_names :
				if category_name and category_name not in seen :
					seen.add(category_name)
					category_names.append(category_name)
					added_count += 1
			
			log_success(message = f"✅ {added_count} new categories captured from page {page_index}")
			
			if page_index == MAX_PAGES :
				log_warning(message = f"🛑 Reached requested stop at page {MAX_PAGES}")
				break
			
			next_li = page.locator(selector = "li.page-item.page-next").first
			next_link = next_li.locator(selector_or_locator = 'a[aria-label="next page"]').first
			
			li_class: str = next_li.get_attribute(name = "class") or ""
			if "disabled" in li_class :
				log_warning(message = "🔚 Reached the last available page")
				break
			
			first_row_before: str = normalize_text(
				text = table.locator(selector_or_locator = "tbody tr td:nth-child(2) a").first.inner_text()
			)
			
			log_info(message = "👉 Clicking next page")
			next_link.click()
			human_sleep_after_click()
			
			try :
				page.wait_for_function(
					expression = """
                    ([selector, previous_text]) => {
                        const element = document.querySelector(selector);
                        if (!element) return false;
                        const current_text = element.innerText
                            .replace(/\\u00a0/g, " ")
                            .replace(/\\s+/g, " ")
                            .trim();
                        return current_text !== previous_text;
                    }
                    """,
					arg = ["table tbody tr td:nth-child(2) a", first_row_before],
					timeout = 10000,
				)
			except PlaywrightTimeoutError :
				log_error(message = "❌ The table did not update after clicking next page")
				break
			
			page_index += 1
		
		write_categories_csv(file_path = OUTPUT_FILE, category_names = category_names)
		log_success(message = f"🎉 Done: {len(category_names)} unique categories saved to '{OUTPUT_FILE}'")
		context.close()


if __name__ == "__main__" :
	main()
