"""Google Sheets integration for writing game data."""

from pathlib import Path

import gspread
import yaml
from google.oauth2.service_account import Credentials

from parser import GameInfo

# Column mapping (1-indexed): A=Name, B=Other work, C=Complete, D=Developer,
# E=Note, F=Link, G=Version, H=Engine, I=Resolved
SHEET_NAME = "Main"
LINK_COLUMN = 6  # Column F

# Paths relative to the script location
SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = SCRIPT_DIR / "bongo-sheet-f6a15e58c2fc.json"
SHEET_ID_FILE = SCRIPT_DIR / "sheet-id.yml"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_sheet_id() -> str:
    """Read the Google Sheet ID from the YAML config."""
    with open(SHEET_ID_FILE, "r") as f:
        config = yaml.safe_load(f)
    return config["SHEET_ID"]


def get_client() -> gspread.Client:
    """Create an authenticated gspread client using service account."""
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_FILE), scopes=SCOPES
    )
    return gspread.authorize(creds)


def get_worksheet() -> gspread.Worksheet:
    """Get the 'Main' worksheet from the configured spreadsheet."""
    client = get_client()
    sheet_id = get_sheet_id()
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet(SHEET_NAME)


def write_game_data(game: GameInfo) -> tuple[int, bool, list[str]]:
    """Write game data to the Google Sheet.

    If a row with matching name, developer, or link already exists,
    replace that row's data instead.

    Args:
        game: GameInfo dataclass with parsed game data.

    Returns:
        A tuple of (row_number, is_replaced, list_of_change_strings)
    """
    worksheet = get_worksheet()
    all_values = worksheet.get_all_values()

    target_row_idx = None
    changes = []

    parsed_name = game.name.strip().lower()
    parsed_dev = game.developer.strip().lower()
    parsed_link = game.link.rstrip("/").lower()

    for i, row in enumerate(all_values):
        existing_name = row[0].strip().lower() if len(row) > 0 else ""
        existing_dev = row[3].strip().lower() if len(row) > 3 else ""
        existing_link = row[5].rstrip("/").lower() if len(row) > 5 else ""

        match = False
        if parsed_link and existing_link == parsed_link:
            match = True
        elif parsed_name and (parsed_name == existing_name or parsed_name == existing_dev):
            match = True
        elif parsed_dev and (parsed_dev == existing_name or parsed_dev == existing_dev):
            match = True

        if match:
            target_row_idx = i + 1  # 1-indexed

            # Record what changed
            old_name = row[0] if len(row) > 0 else ""
            old_dev = row[3] if len(row) > 3 else ""
            old_ver = row[6] if len(row) > 6 else ""

            if old_name != game.name:
                changes.append(f"Name: {old_name} -> {game.name}")
            if old_dev != game.developer:
                changes.append(f"Dev: {old_dev} -> {game.developer}")
            if old_ver != game.version:
                changes.append(f"Ver: {old_ver} -> {game.version}")

            break

    is_replaced = target_row_idx is not None
    if not is_replaced:
        target_row_idx = len(all_values) + 1
        for i, row in enumerate(all_values):
            if i == 0:  # Skip header
                continue
            name = row[0].strip() if len(row) > 0 else ""
            link = row[5].strip() if len(row) > 5 else ""
            if not name and not link:
                target_row_idx = i + 1
                break

    # Preserve Note (E) and Resolved (I) if replacing
    note = ""
    resolved = False
    if is_replaced and target_row_idx <= len(all_values):
        old_row = all_values[target_row_idx - 1]
        note = old_row[4] if len(old_row) > 4 else ""
        resolved = old_row[8].strip().upper() == "TRUE" if len(old_row) > 8 else False

    # Prepare the row data
    row_data = [
        game.name,            # A: Name
        game.other_work,      # B: Other work (bool → checkbox)
        game.complete,        # C: Complete (bool → checkbox)
        game.developer,       # D: Developer
        note,                 # E: Note
        game.link,            # F: Link
        game.version,         # G: Version
        game.engine,          # H: Engine
        resolved,             # I: Resolved
    ]

    cell_range = f"A{target_row_idx}:I{target_row_idx}"
    worksheet.update(
        cell_range,
        [row_data],
        value_input_option="USER_ENTERED",
    )

    return target_row_idx, is_replaced, changes
