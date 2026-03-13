import random
import time

from termcolor import cprint


def normalize_text (text: str) -> str :
	return " ".join(text.replace("\xa0", " ").split())


def log_info (message: str) -> None :
	cprint(text = message, color = "cyan")


def log_success (message: str) -> None :
	cprint(text = message, color = "green")


def log_warning (message: str) -> None :
	cprint(text = message, color = "yellow")


def log_error (message: str) -> None :
	cprint(text = message, color = "red")


def human_sleep_before_parse () -> None :
	delay: float = random.uniform(.5, 1.5)
	log_info(message = f"⏳ Human-like pause before parsing: {delay:.2f}s")
	time.sleep(delay)


def human_sleep_after_click () -> None :
	delay: float = random.uniform(.5, 1.5)
	log_info(message = f"⏳ Human-like pause after click: {delay:.2f}s")
	time.sleep(delay)
