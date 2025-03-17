from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime
from dateutil.parser import parse as date_parse

# --- Configuration ---
IMG_WIDTH = 800
MARGIN = 20
HEADER_FONT_SIZE = 24
ROW_FONT_SIZE = 20
ROW_SPACING = 10          # vertical padding between rows
EXTRA_LINE_SPACING = 8    # additional spacing between lines within a cell

# Define table columns: Date, Title, Location, Genre
col_names = ["Date", "Title", "Location", "Genre"]
# The available width is IMG_WIDTH - 2*MARGIN = 760
col_widths = [100, 250, 200, 210]  # Sum = 760

# Load fonts (adjust font path if necessary)
try:
    header_font = ImageFont.truetype("arial.ttf", HEADER_FONT_SIZE)
    row_font = ImageFont.truetype("arial.ttf", ROW_FONT_SIZE)
except IOError:
    header_font = ImageFont.load_default()
    row_font = ImageFont.load_default()

# --- Load cached gigs data and select one day's gigs ---
with open("cached_gigs.json", "r") as f:
    gigs = json.load(f)

# Group gigs by date (using parsed date)
def group_gigs_by_date(gigs):
    groups = {}
    for gig in gigs:
        try:
            dt = date_parse(gig['date'])
        except Exception:
            continue
        groups.setdefault(dt.date(), []).append(gig)
    return groups

groups = group_gigs_by_date(gigs)
today = datetime.now().date()
if today in groups:
    day_to_use = today
else:
    upcoming_days = sorted([d for d in groups.keys() if d >= today])
    day_to_use = upcoming_days[0] if upcoming_days else None

if not day_to_use:
    raise ValueError("No upcoming gigs found.")

todays_gigs = groups[day_to_use]

# --- Create a dummy image for measurements ---
dummy_img = Image.new("RGB", (IMG_WIDTH, 100), "white")
draw_dummy = ImageDraw.Draw(dummy_img)

# --- Text Wrapping Function ---
def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        test_width = bbox[2] - bbox[0]
        if test_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

# --- Prepare Header ---
full_date = datetime.combine(day_to_use, datetime.min.time()).strftime("%A, %d %B %Y")
header_bbox = draw_dummy.textbbox((0, 0), full_date, font=header_font)
header_height = header_bbox[3] - header_bbox[1]
HEADER_HEIGHT = header_height + 20  # adding some padding

# --- Process Each Gig Row ---
table_rows = []
for gig in todays_gigs:
    # For each gig, define the cell text for each column.
    cell_texts = [
        gig.get("date", ""),
        gig.get("title", ""),
        gig.get("location", ""),
        gig.get("genre", "N/A")
    ]
    wrapped_cells = []
    line_counts = []
    for i, text in enumerate(cell_texts):
        # Subtract some padding from the cell width.
        lines = wrap_text(text, row_font, col_widths[i] - 10, draw_dummy)
        wrapped_cells.append(lines)
        line_counts.append(len(lines))
    max_lines = max(line_counts) if line_counts else 1
    # Measure a sample line height using textbbox.
    sample_bbox = draw_dummy.textbbox((0, 0), "A", font=row_font)
    base_line_height = sample_bbox[3] - sample_bbox[1]
    effective_line_height = base_line_height + EXTRA_LINE_SPACING
    row_height = max_lines * effective_line_height + 10  # add extra padding for the row
    table_rows.append((wrapped_cells, row_height))

# --- Calculate Total Image Height ---
total_rows_height = sum(row_height for _, row_height in table_rows)
IMG_HEIGHT = MARGIN*2 + HEADER_HEIGHT + total_rows_height

# --- Create Final Image ---
img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), "white")
draw = ImageDraw.Draw(img)

# Draw Header Background
draw.rectangle([MARGIN, MARGIN, IMG_WIDTH - MARGIN, MARGIN + HEADER_HEIGHT], fill="black")

# Determine x positions for column boundaries
x_positions = [MARGIN]
for w in col_widths:
    x_positions.append(x_positions[-1] + w)

# Draw Header Text (centered)
for i, col in enumerate(col_names):
    bbox = draw.textbbox((0, 0), col, font=header_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    cell_left = x_positions[i]
    cell_width = col_widths[i]
    text_x = cell_left + (cell_width - text_width) / 2
    text_y = MARGIN + (HEADER_HEIGHT - text_height) / 2
    draw.text((text_x, text_y), col, font=header_font, fill="white")

# Draw vertical grid lines for header
for x in x_positions:
    draw.line([(x, MARGIN), (x, MARGIN + HEADER_HEIGHT)], fill="black", width=2)

# Draw Rows
current_y = MARGIN + HEADER_HEIGHT
for wrapped_cells, row_height in table_rows:
    # Draw horizontal grid line at top of row
    draw.line([(MARGIN, current_y), (IMG_WIDTH - MARGIN, current_y)], fill="black", width=2)
    for i, lines in enumerate(wrapped_cells):
        cell_left = x_positions[i]
        cell_width = col_widths[i]
        total_text_height = len(lines) * effective_line_height
        start_y = current_y + (row_height - total_text_height) / 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=row_font)
            text_width = bbox[2] - bbox[0]
            text_x = cell_left + (cell_width - text_width) / 2
            draw.text((text_x, start_y), line, font=row_font, fill="black")
            start_y += effective_line_height
    current_y += row_height
draw.line([(MARGIN, current_y), (IMG_WIDTH - MARGIN, current_y)], fill="black", width=2)
for x in x_positions:
    draw.line([(x, MARGIN), (x, current_y)], fill="black", width=2)

img.save("todays_gigs_table.png")
print("Image saved as todays_gigs_table.png")
