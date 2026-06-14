import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

sys.path.append(str(Path(__file__).parent))

from src.database import PaperDatabase
from src.account import PaperAccount

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Test_PaperAccount")


def test_paper_account():
    logger.info("=== Starting PaperAccount Tests ===\n")

    db = None
    account = None

    try:
        db = PaperDatabase()
        if db.client is None:
            logger.warning("Supabase client not initialized. Running validation-only tests.")
        else:
            account = PaperAccount(db_client=db)
            logger.info("Supabase connected successfully. Full tests enabled.\n")

    except Exception as e:
        logger.warning(f"Database connection failed: {e}. Running validation-only tests.\n")

    # =====================
    # TEST CASES
    # =====================

    test_cases = [
        ("ALGO_01", 5_000_000, "Valid account"),
        ("STRAT_50", 10_000_000, "Valid account"),
        ("invalid_name", 1_000_000, "Lowercase name (should fail)"),
        ("THIS_NAME_IS_WAY_TOO_LONG_123", 1_000_000, "Name too long (should fail)"),
        ("NEG_MARGIN", -500_000, "Negative margin (should fail)"),
        ("BIG_MARGIN", 150_000_000_00, "Margin > 100 Cr (should fail)"),
    ]

    for name, margin, description in test_cases:
        logger.info(f"TEST: {description}")
        if account:
            result = account.create(account_name=name, initial_margin=margin)
        else:
            # Fallback: test only validation if DB not available
            temp_account = PaperAccount(db_client=type('obj', (object,), {'client': None})())
            result = temp_account.create(account_name=name, initial_margin=margin)
        print(f"Result → {result}\n")

    logger.info("=== All Tests Completed ===")


if __name__ == "__main__":
    test_paper_account()