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


def check_duplicate(worksheet: gspread.Worksheet, url: str) -> bool:
    """Check if a URL already exists in the Link column."""
    # Get all values from the Link column (F = column 6)
    link_values = worksheet.col_values(LINK_COLUMN)
    # Normalize URLs for comparison (strip trailing slashes)
    normalized_url = url.rstrip("/").lower()
    for link in link_values:
        if link.rstrip("/").lower() == normalized_url:
            return True
    return False


def find_next_row(worksheet: gspread.Worksheet) -> int:
    """Find the next empty row in the sheet."""
    # Get all values from column A to find the last occupied row
    all_values = worksheet.col_values(1)  # Column A
    return len(all_values) + 1


def write_game_data(game: GameInfo) -> int:
    """Write game data to the next available row in the Google Sheet.

    Args:
        game: GameInfo dataclass with parsed game data.

    Returns:
        The row number where data was written.

    Raises:
        ValueError: If the URL already exists in the sheet.
    """
    worksheet = get_worksheet()

    # Check for duplicates
    if check_duplicate(worksheet, game.link):
        raise ValueError(f"This link already exists in the sheet: {game.link}")

    # Find the next empty row
    next_row = find_next_row(worksheet)

    # Prepare the row data
    # Columns: A=Name, B=Other work, C=Complete, D=Developer, E=Note, F=Link,
    #          G=Version, H=Engine, I=Resolved
    row_data = [
        game.name,            # A: Name
        game.other_work,      # B: Other work (bool → checkbox)
        game.complete,        # C: Complete (bool → checkbox)
        game.developer,       # D: Developer
        "",                   # E: Note (leave empty)
        game.link,            # F: Link
        game.version,         # G: Version
        game.engine,          # H: Engine
        False,                # I: Resolved (default unchecked)
    ]

    # Write the row using update to handle booleans properly for checkboxes
    cell_range = f"A{next_row}:I{next_row}"
    worksheet.update(
        cell_range,
        [row_data],
        value_input_option="USER_ENTERED",
    )

    return next_row
