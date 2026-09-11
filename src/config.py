from pathlib import Path
import os

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

CORRIDORS_PATH = ROOT / "corridors.csv"

TRAIN_PATH = (
    ROOT
    / "data"
    / "processed"
    / "forecasting_train_preprocessed.csv"
)

HISTORY_PATH = (
    ROOT
    / "data"
    / "web"
    / "historical_top14.csv"
)

ENV_PATH = ROOT / ".env"


load_dotenv(
    dotenv_path=ENV_PATH,
    override=False
)


TOMTOM_API_KEY = os.getenv(
    "TOMTOM_API_KEY"
)


DISPLAY_NAMES = {
    "tt_bekasi": "Bekasi",
    "tt_bogor": "Bogor",
    "tt_bsd": "BSD",
    "tt_cawang": "Cawang",
    "tt_depok": "Depok",
    "tt_gatsu": "Gatot Subroto",
    "tt_grogol": "Grogol",
    "tt_kebonjeruk": "Kebon Jeruk",
    "tt_kelapagading": "Kelapa Gading",
    "tt_kuningan": "Kuningan",
    "tt_sudirman": "Sudirman",
    "tt_tangerang": "Tangerang",
    "tt_tbsimatupang": "TB Simatupang",
    "tt_thamrin": "Thamrin",
}