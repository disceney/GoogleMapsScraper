from __future__ import annotations

import re
from urllib.parse import unquote, urljoin

from playwright.sync_api import Page

from utils import log_info

EMAIL_PATTERN: re.Pattern[str] = re.compile(
	pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
)

# Obfuscation replacements: (regex pattern -> replacement).
# Order matters: replace @ substitutes first, then dot substitutes.
AT_OBFUSCATIONS: list[tuple[str, str]] = [
	(r"\s*\[\s*at\s*\]\s*", "@"),
	(r"\s*\(\s*at\s*\)\s*", "@"),
	(r"\s*\{\s*at\s*\}\s*", "@"),
	(r"\s*\[\s*arobase\s*\]\s*", "@"),
	(r"\s*\(\s*arobase\s*\)\s*", "@"),
	(r"\s*\[\s*@\s*\]\s*", "@"),
	(r"\s*\(\s*@\s*\)\s*", "@"),
	(r"\s*\[\s*a\s*\]\s*", "@"),
	(r"\s+at\s+", "@"),
]

DOT_OBFUSCATIONS: list[tuple[str, str]] = [
	(r"\s*\[\s*dot\s*\]\s*", "."),
	(r"\s*\(\s*dot\s*\)\s*", "."),
	(r"\s*\[\s*point\s*\]\s*", "."),
	(r"\s*\(\s*point\s*\)\s*", "."),
	(r"\s*\[\s*\.\s*\]\s*", "."),
	(r"\s*\(\s*\.\s*\)\s*", "."),
]

IGNORED_EMAIL_DOMAINS: set[str] = {
	"example.com",
	"example.org",
	"sentry.io",
	"wixpress.com",
	"googleapis.com",
	"googleusercontent.com",
	"google.com",
	"gstatic.com",
	"w3.org",
	"schema.org",
	"json-ld.org",
	"gravatar.com",
	"wordpress.org",
	"wordpress.com",
	"wp.com",
}

IGNORED_EMAIL_PREFIXES: tuple[str, ...] = (
	"noreply@",
	"no-reply@",
	"postmaster@",
	"mailer-daemon@",
	"webmaster@",
)

CONTACT_PAGE_KEYWORDS: list[str] = [
	"contact",
	"nous-contacter",
	"nous contacter",
	"contactez",
	"a-propos",
	"à propos",
	"about",
	"mentions-legales",
	"mentions legales",
	"mentions légales",
	"cgv",
	"cgu",
	"privacy",
	"politique-de-confidentialite",
	"politique de confidentialité",
	"legal",
	"impressum",
	"info",
	"equipe",
	"team",
	"qui-sommes-nous",
	"qui sommes nous",
	"notre-equipe",
	"notre équipe",
	"societe",
	"société",
	"entreprise",
	"coordonnees",
	"coordonnées",
	"service-client",
	"service client",
	"support",
	"assistance",
	"aide",
	"sav",
	"nous-joindre",
	"recrutement",
	"carrieres",
	"carrières",
	"presse",
	"partenaires",
	"partenariats",
	"conditions-generales",
	"conditions générales",
	"conditions-generales-de-vente",
	"conditions générales de vente",
	"conditions-generales-d-utilisation",
	"conditions générales d'utilisation",
	"donnees-personnelles",
	"données personnelles",
	"politique-cookies",
	"politique cookies",
	"cookies",
	"editeur",
	"éditeur",
	"hebergement",
	"hébergement",
	"informations-legales",
	"informations légales",
	"plan-du-site",
	"plan du site",
	"contact-us",
	"contact us",
	"get-in-touch",
	"get in touch",
	"reach-us",
	"reach us",
	"about-us",
	"about us",
	"our-team",
	"our team",
	"company",
	"support-center",
	"support center",
	"help-center",
	"help center",
	"help",
	"customer-service",
	"customer service",
	"customer-support",
	"customer support",
	"support-us",
	"careers",
	"jobs",
	"press",
	"media",
	"partners",
	"partnerships",
	"legal-notice",
	"legal-notices",
	"terms",
	"terms-of-service",
	"terms of service",
	"terms-and-conditions",
	"terms and conditions",
	"privacy-policy",
	"privacy policy",
	"cookie-policy",
	"cookie policy",
	"cookies-policy",
	"faq",
	"faqs",
	"locations",
	"offices",
	"corporate",
	"editorial",
	"staff",
	"directory",
	"sitemap",
	"tarifs",
	"price"
]


def sanitize_email (email: str) -> str :
	cleaned: str = unquote(string = email).strip()
	cleaned = cleaned.strip()
	match = EMAIL_PATTERN.search(string = cleaned)
	
	if match is not None :
		return match.group(0)
	
	return ""


def is_valid_email (email: str) -> bool :
	lower: str = email.lower()
	
	domain: str = lower.split("@", 1)[-1]
	
	if domain in IGNORED_EMAIL_DOMAINS :
		return False
	
	if lower.startswith(IGNORED_EMAIL_PREFIXES) :
		return False
	
	if ".min." in lower or ".bundle." in lower :
		return False
	
	local_part: str = lower.split("@", 1)[0]
	
	if local_part.isdigit() :
		return False
	
	return True


def deobfuscate_emails (text: str) -> str :
	"""
	Replace common email obfuscation patterns in *text* so that the
	standard EMAIL_PATTERN regex can find them.

	Handles: [at], (at), {at}, [arobase], (arobase), [@], (@), [a],
	         " at ", [dot], (dot), [point], (point), [.], (.)
	"""
	result: str = text

	for pattern, replacement in AT_OBFUSCATIONS :
		result = re.sub(pattern = pattern, repl = replacement, string = result, flags = re.IGNORECASE)

	for pattern, replacement in DOT_OBFUSCATIONS :
		result = re.sub(pattern = pattern, repl = replacement, string = result, flags = re.IGNORECASE)

	return result


def extract_emails_from_text (text: str) -> list[str] :
	"""Return all valid, deduplicated emails found in *text*."""
	# Search in both original and deobfuscated text
	combined_text: str = text + "\n" + deobfuscate_emails(text = text)

	raw_matches: list[str] = EMAIL_PATTERN.findall(string = combined_text)
	seen: set[str] = set()
	results: list[str] = []

	for raw_email in raw_matches :
		email: str = sanitize_email(email = raw_email)

		if not email :
			continue

		lower: str = email.lower()

		if lower in seen :
			continue

		seen.add(lower)

		if is_valid_email(email = email) :
			results.append(email)

	return results


def extract_email_from_page (page: Page) -> str :
	try :
		mailto_links = page.locator(selector = 'a[href^="mailto:"]')
		count: int = mailto_links.count()
		
		for i in range(count) :
			try :
				href: str | None = mailto_links.nth(i).get_attribute(name = "href", timeout = 2000)
				if href and href.startswith("mailto:") :
					raw: str = href.replace("mailto:", "", 1).split("?")[0].strip()
					email: str = sanitize_email(email = raw)
					if email and is_valid_email(email = email) :
						return email
			except Exception :
				continue
	except Exception :
		pass
	
	try :
		body_text: str = page.locator(selector = "body").inner_text(timeout = 5000)
		emails: list[str] = extract_emails_from_text(text = body_text)
		if emails :
			return emails[0]
	except Exception :
		pass
	
	try :
		html: str = page.content()
		emails = extract_emails_from_text(text = html)
		if emails :
			return emails[0]
	except Exception :
		pass
	
	return ""


def find_contact_page_urls (page: Page) -> list[str] :
	base_url: str = page.url
	found_urls: list[str] = []
	seen: set[str] = set()
	
	try :
		links = page.locator(selector = "a[href]")
		count: int = links.count()
		
		for i in range(count) :
			try :
				href: str | None = links.nth(i).get_attribute(name = "href", timeout = 1000)
				link_text: str = ""
				
				try :
					link_text = links.nth(i).inner_text(timeout = 1000)
				except Exception :
					pass
				
				if not href :
					continue
				
				if href.startswith(("#", "javascript:", "tel:", "mailto:")) :
					continue
				
				full_url: str = urljoin(base = base_url, url = href).split("#")[0]
				
				if full_url in seen :
					continue
				
				combined: str = f"{href} {link_text}".lower()
				
				for keyword in CONTACT_PAGE_KEYWORDS :
					if keyword in combined :
						seen.add(full_url)
						found_urls.append(full_url)
						break
			except Exception :
				continue
	except Exception :
		pass
	
	return found_urls


def extract_email_from_website (page: Page) -> str :
	email: str = extract_email_from_page(page = page)
	if email :
		return email
	
	sub_urls: list[str] = find_contact_page_urls(page = page)
	
	if sub_urls :
		log_info(message = f"  Checking {len(sub_urls)} sub-page(s) for email...")
	
	for sub_url in sub_urls :
		try :
			page.goto(url = sub_url, wait_until = "domcontentloaded", timeout = 10000)
			
			email = extract_email_from_page(page = page)
			if email :
				return email
		except Exception :
			continue
	
	return ""
