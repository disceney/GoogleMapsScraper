from __future__ import annotations

from pathlib import Path

CATEGORIES_FILE: str = "categories.csv"
COMPANIES_FILE: str = "companies.csv"
CHROME_AUTOMATION_PROFILE_DIR: str = str(Path.cwd() / "chrome-profile")
CHROME_EXECUTABLE_PATH: str = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
GOOGLE_MAPS_SEARCH_URL: str = "https://www.google.com/maps/search/{query}"

COMPANY_FIELDNAMES: list[str] = [
	"business_name",
	"category_name",
	"address",
	"phone",
	"website",
	"rating",
	"review_count",
	"email",
	"google_maps_url",
]
