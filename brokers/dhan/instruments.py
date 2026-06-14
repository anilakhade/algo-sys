import os
import logging
import collections
import pandas as pd 
from datetime import datetime

logger = logging.getLogger(__name__)

class DhanInstruments:
    def __init__(self, auth_provider):
        self.auth = auth_provider
        self.logger = logger

        self.cache_dir = os.path.join("data", "dhan")
        self.cache_file = os.path.join(self.cache_dir, "dhan_instruments.csv")
        self.download_url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        self.df = None

        # Lightning-fast nested database memory caches (O(1) Hash Maps)
        self.equity_index_map = collections.defaultdict(lambda: collections.defaultdict(dict))
        self.futures_map = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(dict)))
        self.options_map = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(dict)))))

    def download(self) -> pd.DataFrame:
        os.makedirs(self.cache_dir, exist_ok=True)

        if os.path.exists(self.cache_file):
            file_modified_date = datetime.fromtimestamp(os.path.getmtime(self.cache_file)).date()
            current_date = datetime.today().date()

            if file_modified_date == current_date:
                self.logger.info("Using existing Instrument Master. Loading to RAM...")
                self.df = pd.read_csv(self.cache_file, low_memory=False)
                self._build_index_structures()
                return self.df

        self.logger.info("Instrument Master file missing or old. Downloading fresh copy from server...")
        try:
            self.df = pd.read_csv(self.download_url, low_memory=False)
            self.df.to_csv(self.cache_file, index=False)
            self.logger.info(f"Successfully cached {len(self.df)} instruments locally on disk.")
            self._build_index_structures()
            return self.df

        except Exception as e:
            self.logger.error(f"Critical error downloading or processing master instrument file: {e}")
            raise

    def _build_index_structures(self):
        """
        Processes the raw DataFrame into structured memory hash maps.
        Implements a hybrid approach using SEM_TRADING_SYMBOL for cash/indices,
        and SEM_CUSTOM_SYMBOL parsing for complex multi-exchange derivatives.
        """
        self.logger.info("Compiling high-performance in-memory search grid...")
        
        # Reset internal maps to avoid duplicate overlays on reload
        self.equity_index_map.clear()
        self.futures_map.clear()
        self.options_map.clear()

        # Iterate through the rows using a fast row namedtuple scanner
        for row in self.df.itertuples(index=False):
            # Safe boundary check: skip rows missing vital data fields
            if pd.isna(row.SEM_SMST_SECURITY_ID) or pd.isna(row.SEM_INSTRUMENT_NAME):
                continue

            exchange = str(row.SEM_EXM_EXCH_ID).upper()
            instrument = str(row.SEM_INSTRUMENT_NAME).upper()
            
            # Format our standard systemic output package structure
            asset_pack = {
                "token": str(row.SEM_SMST_SECURITY_ID),
                "lot_size": int(row.SEM_LOT_UNITS) if pd.notna(row.SEM_LOT_UNITS) else 1,
                "tick_size": float(row.SEM_TICK_SIZE) if pd.notna(row.SEM_TICK_SIZE) else 0.05,
                "segment": instrument,
                "exchange": exchange,
                "trading_symbol": str(row.SEM_TRADING_SYMBOL).upper()
            }

            # SCENARIO A: Equity Cash & Spot Indices -> Index by standard trading ticker symbol
            if instrument in ["EQUITY", "INDEX"]:
                trading_symbol = str(row.SEM_TRADING_SYMBOL).upper()
                self.equity_index_map[exchange][instrument][trading_symbol] = asset_pack

            # SCENARIO B: Futures Contracts -> Parse via space-separated custom description
            elif instrument in ["FUTIDX", "FUTSTK", "FUTCOM", "FUTCUR"]:
                if pd.isna(row.SEM_CUSTOM_SYMBOL):
                    continue
                custom_symbol_str = str(row.SEM_CUSTOM_SYMBOL).upper()
                tokens = custom_symbol_str.split()
                
                if len(tokens) >= 3:
                    root_symbol = tokens[0]
                    expiry_month = tokens[1]
                    self.futures_map[exchange][instrument][root_symbol][expiry_month] = asset_pack

            # SCENARIO C: Options Contracts -> Parse via precision token split mapping
            elif instrument in ["OPTIDX", "OPTSTK", "OPTFUT", "OPTCUR"]:
                if pd.isna(row.SEM_CUSTOM_SYMBOL):
                    continue
                custom_symbol_str = str(row.SEM_CUSTOM_SYMBOL).upper()
                tokens = custom_symbol_str.split()
                
                if len(tokens) >= 5:
                    root_symbol = tokens[0]
                    expiry_date = f"{tokens[1]} {tokens[2]}" # Combines Day + Month (e.g., '23 JUN')
                    
                    # Stripe Price Normalization: strip trailing decimal zeroes safely
                    raw_strike = float(tokens[3])
                    strike_key = str(int(raw_strike)) if raw_strike.is_integer() else str(raw_strike)
                    
                    option_type = tokens[4] # 'CALL' or 'PUT'
                    self.options_map[exchange][instrument][root_symbol][expiry_date][strike_key][option_type] = asset_pack

        self.logger.info("Search grid compilation complete. System armed for instant lookups.")

    def get_token(self, symbol: str, exchange: str = "NSE", instrument: str = "EQUITY", 
                  expiry: str = None, strike: float = None, option_type: str = None) -> dict:
        """
        Instantly extracts an instrument asset packet from high-speed memory maps.
        """
        if self.df is None:
            self.download()

        try:
            exch_upper = exchange.upper()
            inst_upper = instrument.upper()
            sym_upper = symbol.upper()

            # 1. Handle Cash & Spot Index routing
            if inst_upper in ["EQUITY", "INDEX"]:
                asset = self.equity_index_map[exch_upper][inst_upper].get(sym_upper)
                if not asset:
                    self.logger.warning(f"Lookup Miss (Cash): {exch_upper}:{inst_upper}:{sym_upper}")
                return asset

            # 2. Handle Futures routing
            elif inst_upper in ["FUTIDX", "FUTSTK", "FUTCOM", "FUTCUR"]:
                if not expiry:
                    self.logger.error(f"Lookup Aborted: Futures for {sym_upper} require the 'expiry' month string.")
                    return None
                
                asset = self.futures_map[exch_upper][inst_upper][sym_upper].get(expiry.upper())
                if not asset:
                    self.logger.warning(f"Lookup Miss (Futures): {exch_upper}:{inst_upper}:{sym_upper} for Expiry Month: {expiry.upper()}")
                return asset

            # 3. Handle Options routing
            elif inst_upper in ["OPTIDX", "OPTSTK", "OPTFUT", "OPTCUR"]:
                if not all([expiry, strike, option_type]):
                    self.logger.error(f"Lookup Aborted: Options for {sym_upper} require expiry, strike, and option_type parameters.")
                    return None
                
                # Normalize option shorthand strings seamlessly
                opt_upper = option_type.upper()
                mapped_type = "CALL" if opt_upper in ["CE", "CALL"] else "PUT" if opt_upper in ["PE", "PUT"] else opt_upper

                # Normalize the strike lookup key identically to compilation rules
                raw_strike = float(strike)
                strike_key = str(int(raw_strike)) if raw_strike.is_integer() else str(raw_strike)

                asset = self.options_map[exch_upper][inst_upper][sym_upper][expiry.upper()][strike_key].get(mapped_type)
                if not asset:
                    self.logger.warning(f"Lookup Miss (Options): {exch_upper}:{inst_upper}:{sym_upper} at {expiry.upper()} strike {strike_key} {mapped_type}")
                return asset

            self.logger.error(f"Lookup Denied: Unrecognized systemic instrument configuration name: {inst_upper}")
            return None

        except Exception as e:
            self.logger.error(f"Search Execution Fault for asset {symbol}: {e}")
            return None