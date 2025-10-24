import logging
import sys
from pathlib import Path

def setup_logging():
    """Setup logging configuration"""
    logs_dir = Path(__file__).parent.parent.parent / "data" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = logs_dir / "lumi_companion.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("LumiCompanion")