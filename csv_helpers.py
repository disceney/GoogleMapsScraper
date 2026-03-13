from __future__ import annotations

import csv
from pathlib import Path

from config import COMPANY_FIELDNAMES
from utils import normalize_text


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


def load_companies (file_path: str) -> list[dict[str, str]] :
	path: Path = Path(file_path)
	
	if not path.exists() :
		raise FileNotFoundError(f"Companies file not found: {file_path}")
	
	with open(file = file_path, mode = "r", encoding = "utf-8", newline = "") as file_handle :
		reader = csv.DictReader(f = file_handle)
		return list(reader)


def save_companies (file_path: str, companies: list[dict[str, str]]) -> None :
	with open(file = file_path, mode = "w", encoding = "utf-8", newline = "") as file_handle :
		writer = csv.DictWriter(
			f = file_handle,
			fieldnames = COMPANY_FIELDNAMES,
		)
		writer.writeheader()
		writer.writerows(companies)


def build_company_keys (business_name: str, google_maps_url: str, category_name: str = "", address: str = "") -> list[str] :
	keys: list[str] = []
	normalized_name: str = normalize_text(text = business_name).casefold()
	normalized_url: str = google_maps_url.strip()
	normalized_category: str = normalize_text(text = category_name).casefold()
	normalized_address: str = normalize_text(text = address).casefold()
	
	if normalized_url :
		keys.append(f"url::{normalized_url}")
	
	if normalized_name and normalized_category and normalized_address :
		keys.append(f"identity::{normalized_name}|{normalized_category}|{normalized_address}")
	elif normalized_name and normalized_address :
		keys.append(f"identity::{normalized_name}||{normalized_address}")
	
	if normalized_name and not keys :
		keys.append(f"name::{normalized_name}")
	
	return keys


def load_existing_company_keys (file_path: str) -> set[str] :
	path: Path = Path(file_path)
	existing_keys: set[str] = set()
	
	if not path.exists() :
		return existing_keys
	
	with open(file = file_path, mode = "r", encoding = "utf-8", newline = "") as file_handle :
		reader = csv.DictReader(f = file_handle)
		
		for row in reader :
			row_keys: list[str] = build_company_keys(
				business_name = (row.get("business_name") or ""),
				google_maps_url = (row.get("google_maps_url") or ""),
				category_name = (row.get("category_name") or ""),
				address = (row.get("address") or ""),
			)
			existing_keys.update(row_keys)
	
	return existing_keys
