import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List

# === Configuration ===
OUTPUT_DIR = "generated_test_docs"
CANVAS_SIZE = (800, 1100)  # A4-ish aspect ratio
BG_COLOR = "white"
TEXT_COLOR = "black"
HEADER_COLOR = "darkblue"
SECTION_COLOR = "darkred"

# Try to load better fonts, fallback to default if not found
try:
    # Common paths for Windows/Linux fonts - adjusted for standard environments
    font_path_bold = "arialbd.ttf"
    font_path_reg = "arial.ttf"

    FONT_HEADER = ImageFont.truetype(font_path_bold, 24)
    FONT_SUBHEADER = ImageFont.truetype(font_path_bold, 18)
    FONT_LABEL = ImageFont.truetype(font_path_bold, 16)
    FONT_TEXT = ImageFont.truetype(font_path_reg, 16)
    FONT_SMALL = ImageFont.truetype(font_path_reg, 12)
except IOError:
    # Fallback for systems without Arial
    FONT_HEADER = ImageFont.load_default()
    FONT_SUBHEADER = ImageFont.load_default()
    FONT_LABEL = ImageFont.load_default()
    FONT_TEXT = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()

# === Helper Functions ===


def load_test_cases(filename="test_cases.json") -> Dict[str, Any]:
    """Finds and loads the test_cases.json file."""
    paths_to_check = [filename, os.path.join("..", filename)]

    for path in paths_to_check:
        if os.path.exists(path):
            print(f"✅ Found test data at: {path}")
            with open(path, "r") as f:
                return json.load(f)

    print(f"❌ Error: Could not find {filename} in current or parent directory.")
    sys.exit(1)


def create_base_image() -> (Image.Image, ImageDraw.ImageDraw):
    img = Image.new("RGB", CANVAS_SIZE, color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    return img, draw


def draw_header(draw, y_start, title, subtitle_1, subtitle_2):
    y = y_start
    draw.text((50, y), title, fill=HEADER_COLOR, font=FONT_HEADER)
    y += 35
    draw.text((50, y), subtitle_1, fill=TEXT_COLOR, font=FONT_TEXT)
    y += 25
    draw.text((50, y), subtitle_2, fill=TEXT_COLOR, font=FONT_SMALL)
    y += 30
    draw.line((50, y, CANVAS_SIZE[0] - 50, y), fill="gray", width=1)
    return y + 20


def draw_patient_info(draw, y_start, name, date, label_prefix="Patient"):
    y = y_start
    draw.text((50, y), f"{label_prefix} Name:", fill=TEXT_COLOR, font=FONT_LABEL)
    draw.text((180, y), name, fill=TEXT_COLOR, font=FONT_TEXT)

    draw.text((550, y), "Date:", fill=TEXT_COLOR, font=FONT_LABEL)
    draw.text((610, y), date, fill=TEXT_COLOR, font=FONT_TEXT)
    return y + 50


# === Core Generators ===


def generate_prescription(case_id: str, data: Dict[str, Any], output_path: str):
    """Dynamically renders a prescription based on JSON data keys."""
    img, d = create_base_image()
    y = 50

    # 1. Header (Doctor Details)
    doc_name = data.get("doctor_name", "Medical Officer")
    doc_reg = data.get("doctor_reg", "N/A")
    # FIX: Handle None values safely
    clinic_name = data.get("hospital") or "City Medical Center"

    y = draw_header(d, y, clinic_name.upper(), doc_name, f"Reg. No: {doc_reg}")

    # 2. Patient Info
    y = draw_patient_info(
        d, y, data.get("patient_name", "Unknown"), data.get("date", "N/A")
    )

    # 3. Diagnosis (Crucial)
    d.text((50, y), "DIAGNOSIS:", fill=SECTION_COLOR, font=FONT_SUBHEADER)
    y += 30
    diagnosis = data.get("diagnosis", "General Checkup")
    d.text((70, y), diagnosis, fill=TEXT_COLOR, font=FONT_TEXT)
    y += 50

    # 4. Dynamic Treatment Sections

    # A. Medicines List
    medicines = data.get("medicines_prescribed")
    if medicines and isinstance(medicines, list):
        d.text((50, y), "Rx (MEDICINES):", fill=SECTION_COLOR, font=FONT_SUBHEADER)
        y += 30
        for i, med in enumerate(medicines, 1):
            d.text((70, y), f"{i}. {med}", fill=TEXT_COLOR, font=FONT_TEXT)
            y += 25
        y += 20

    # B. Procedures List
    procedures = data.get("procedures")
    if procedures and isinstance(procedures, list):
        d.text((50, y), "PROCEDURES ADVISED:", fill=SECTION_COLOR, font=FONT_SUBHEADER)
        y += 30
        for i, proc in enumerate(procedures, 1):
            d.text((70, y), f"- {proc}", fill=TEXT_COLOR, font=FONT_TEXT)
            y += 25
        y += 20

    # C. Specific Treatment String
    treatment_str = data.get("treatment")
    if treatment_str and isinstance(treatment_str, str):
        d.text((50, y), "TREATMENT PLAN:", fill=SECTION_COLOR, font=FONT_SUBHEADER)
        y += 30
        d.text((70, y), treatment_str, fill=TEXT_COLOR, font=FONT_TEXT)
        y += 40

    # D. Diagnostic Tests List
    tests = data.get("tests_prescribed")
    if tests and isinstance(tests, list):
        d.text((50, y), "DIAGNOSTIC TESTS:", fill=SECTION_COLOR, font=FONT_SUBHEADER)
        y += 30
        for test in tests:
            d.text((70, y), f"[ ] {test}", fill=TEXT_COLOR, font=FONT_TEXT)
            y += 25
        y += 20

    # Footer Signature
    y_footer = CANVAS_SIZE[1] - 150
    d.line((550, y_footer, 750, y_footer), fill="black", width=1)
    d.text((600, y_footer + 10), "(Signature)", fill="gray", font=FONT_SMALL)
    d.text((550, y_footer + 30), doc_name, fill=TEXT_COLOR, font=FONT_TEXT)

    img.save(output_path)
    print(f"   📄 Generated Prescription: {output_path}")


def generate_bill(case_id: str, data: Dict[str, Any], output_path: str):
    """Dynamically renders a bill based on bill item keys in JSON."""
    img, d = create_base_image()
    y = 50

    # 1. Header
    # FIX: Handle None values safely
    hospital_name = (data.get("hospital") or "City Medical Center").upper()
    y = draw_header(d, y, hospital_name, "TAX INVOICE", f"Bill No: INV-{case_id}")

    # 2. Patient Info
    y = draw_patient_info(
        d,
        y,
        data.get("patient_name", "Unknown"),
        data.get("date", "N/A"),
        label_prefix="Billed To",
    )
    y += 20

    # 3. Table Header
    d.rectangle((50, y, CANVAS_SIZE[0] - 50, y + 35), fill="#f0f0f0")
    d.text((70, y + 5), "DESCRIPTION", fill=TEXT_COLOR, font=FONT_LABEL)
    d.text((600, y + 5), "AMOUNT (INR)", fill=TEXT_COLOR, font=FONT_LABEL)
    y += 50

    # 4. Dynamic Bill Items
    bill_items = data.get("bill_items_dict", {})
    total_calculated = 0

    for key, value in bill_items.items():
        if isinstance(value, (int, float)):
            description = key.replace("_", " ").title()
            amount_str = f"₹ {value:,.2f}"

            d.text((70, y), description, fill=TEXT_COLOR, font=FONT_TEXT)
            amount_width = d.textlength(amount_str, font=FONT_TEXT)
            d.text((700 - amount_width, y), amount_str, fill=TEXT_COLOR, font=FONT_TEXT)

            total_calculated += value
            y += 35

    # 5. Total Section
    y += 20
    d.line((50, y, CANVAS_SIZE[0] - 50, y), fill="black", width=2)
    y += 20

    total_str = f"₹ {total_calculated:,.2f}"
    d.text((450, y), "GRAND TOTAL:", fill=HEADER_COLOR, font=FONT_HEADER)

    total_width = d.textlength(total_str, font=FONT_HEADER)
    d.text((700 - total_width, y), total_str, fill=SECTION_COLOR, font=FONT_HEADER)

    # Optional Footer
    if data.get("cashless_request"):
        y += 60
        d.rectangle((50, y, 300, y + 40), outline=SECTION_COLOR, width=2)
        d.text((70, y + 8), "CASHLESS REQUESTED", fill=SECTION_COLOR, font=FONT_LABEL)

    img.save(output_path)
    print(f"   💰 Generated Bill: {output_path}")


# === Main Execution ===


def generate_all_test_docs():
    # 1. Load Data
    json_data = load_test_cases()
    test_cases = json_data.get("test_cases", [])

    # 2. Prepare Output Directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🚀 Starting generation of {len(test_cases)} test case document sets...")
    print(f"📂 Output directory: ./{OUTPUT_DIR}/\n")

    # 3. Iterate and Generate
    for tc in test_cases:
        case_id = tc["case_id"]
        print(f"Processing {case_id}: {tc.get('case_name')}")

        input_data = tc["input_data"]
        documents_node = input_data.get("documents", {})

        # FIX: Ensure common_data does not contain None for hospital
        common_data = {
            "patient_name": input_data.get("member_name"),
            "date": input_data.get("treatment_date"),
        }
        # Only add hospital if it exists, otherwise leave it out so defaults work
        if input_data.get("hospital"):
            common_data["hospital"] = input_data.get("hospital")

        # --- Generate Prescription ---
        if "prescription" in documents_node:
            presc_data = documents_node["prescription"].copy()
            presc_data.update(common_data)

            output_filename = os.path.join(OUTPUT_DIR, f"{case_id}_prescription.jpg")
            generate_prescription(case_id, presc_data, output_filename)

        # --- Generate Bill ---
        if "bill" in documents_node:
            bill_data_raw = documents_node["bill"]
            bill_render_data = common_data.copy()
            bill_render_data["bill_items_dict"] = bill_data_raw

            output_filename = os.path.join(OUTPUT_DIR, f"{case_id}_bill.jpg")
            generate_bill(case_id, bill_render_data, output_filename)

        print("-" * 40)

    print(f"\n✅ Completed! All test documents generated in '{OUTPUT_DIR}'.")


if __name__ == "__main__":
    generate_all_test_docs()
