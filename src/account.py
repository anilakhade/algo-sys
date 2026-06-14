import re
import logging
from typing import Optional
from src.database import PaperDatabase

logger = logging.getLogger("Account_Factory")

class PaperAccount:
    # 100 Crore in Rupees (1,00,00,00,000)
    MAX_MARGIN_LIMIT = 1000000000.00

    def __init__(self, db_client: PaperDatabase):
        self.db = db_client
        self.logger = logger

    def validate_account_name(self, name: str) -> bool:
        """
        Rule: Max 20 characters, alphanumeric and underscores, 
        no spaces, all uppercase. (e.g., ASD_45, STRAT_50)
        """
        if not name or len(name) > 20:
            return False
        # Allows uppercase letters, numbers, and underscores. No spaces allowed.
        pattern = r"^[A-Z0-9_]+$"
        return bool(re.match(pattern, name))

    def create(self, account_name: str, initial_margin: float = 1000000.0) -> dict:
        """
        Validates parameters and saves the certified paper account to Supabase.
        """
        # 1. Clean and check the account name formatting rules
        if not self.validate_account_name(account_name):
            error_msg = f"Rejected: Account name '{account_name}' must be max 20 characters, alphanumeric/underscores, no spaces, and all uppercase."
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        # 2. Check margin boundaries (0 to 100 Crore)
        if initial_margin < 0.0 or initial_margin > self.MAX_MARGIN_LIMIT:
            error_msg = f"Rejected: Margin for '{account_name}' must be between 0 and 100 Crore Rs. Provided: {initial_margin:,.2f}"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        # 3. Save to Supabase using your existing table layout
        self.logger.info(f"Validation passed. Saving paper account '{account_name}' with margin Rs. {initial_margin:,.2f} to database...")
        
        try:
            payload = {
                "account_id": account_name,       #-- Using the name directly as the unique primary key
                "account_name": account_name,
                "initial_cash": float(initial_margin),
                "current_cash": float(initial_margin),
                "available_margin": float(initial_margin),
                "utilized_margin": 0.00,
                "is_active": True
            }
            
            res = self.db.client.table("paper_accounts").upsert(payload).execute()
            self.logger.info(f"Account '{account_name}' successfully live and stored in cloud registry.")
            return {"status": "success", "data": res.data}
            
        except Exception as e:
            error_msg = f"Database insertion failure for account '{account_name}': {str(e)}"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}