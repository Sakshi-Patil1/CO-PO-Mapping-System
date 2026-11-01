import io
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def create_course_export_workbook(department, course, matrix_data, justifications):
    """
    Creates a comprehensive, NBA-compliant Excel workbook for the selected course:
    1. Sheet 'Course Details & COs': Metadata and defined Course Outcomes.
    2. Sheet '12 CO-PO Mapping': NBA Articulation Matrix with only 1, 2, 3, or - in mapping cells,
       and dynamic Excel AVERAGE formulas for columns and rows.
    3. Sheet 'Mapping Justifications': Pedagogical rationale, Bloom taxonomy alignment,
       and Match % for every cell.
    4. Sheet 'Department Outcomes': Official POs, PSOs, and Washington Accord WKs.

    Original workbook is never modified. Output stream is returned.
    """
    wb = openpyxl.Workbook()

    # Styles
    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    navy_sub_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    light_blue_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True)
    title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    subtitle_font = Font(name="Calibri", size=11, italic=True, color="334155")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')
    wrap_align = Alignment(horizontal='left', vertical='center', wrap_text=True)

    cos = course.get("cos", [])
    pos = department.get("po_statements", [])
    psos = department.get("pso_statements", [])
    wks = department.get("wk_statements", [])

    course_name = course.get("course_name", "Course Name")
    course_code = course.get("course_code", "Course Code")
    coordinator = course.get("coordinator", "Course Coordinator")
    class_name = course.get("class_name", "SY B Tech")
    academic_year = course.get("academic_year", "2026-2027")
    semester = course.get("semester", "Odd")
    institution = department.get("institution", "Annasaheb Dange College of Engineering and Technology, Ashta")
    dept_name = department.get("name", "Department of Artificial Intelligence and Data Science")
    program_name = department.get("program", "B Tech")

    # ==========================================
    # SHEET 1: Course Details & CO Statements
    # ==========================================
    ws_details = wb.active
    ws_details.title = "Course Details & COs"

    ws_details.cell(1, 1, value=institution).font = bold_font
    ws_details.cell(2, 1, value=dept_name).font = subtitle_font
    ws_details.cell(3, 1, value=f"Program: {program_name}").font = subtitle_font

    ws_details.cell(5, 1, value="Course Information").font = title_font

    meta_rows = [
        ("Course Name", course_name),
        ("Course Code", course_code),
        ("Class & Semester", f"{class_name} • Semester: {semester}"),
        ("Academic Year", academic_year),
        ("Course Coordinator", coordinator),
        ("Head of Department", course.get("hod", "Head of Department"))
    ]
    for r_idx, (lbl, val) in enumerate(meta_rows, start=6):
        c1 = ws_details.cell(r_idx, 1, value=lbl)
        c1.font = bold_font
        c1.fill = light_blue_fill
        c1.border = thin_border
        c2 = ws_details.cell(r_idx, 2, value=val)
        c2.border = thin_border

    co_start_r = 13
    ws_details.cell(co_start_r, 1, value="Defined Course Outcomes (COs)").font = title_font

    co_headers = ["CO #", "Syllabus Code", "Course Outcome Statement", "Bloom's Taxonomy Level"]
    for c_i, h_text in enumerate(co_headers, start=1):
        c = ws_details.cell(co_start_r + 1, c_i, value=h_text)
        c.fill = navy_fill
        c.font = header_font
        c.alignment = center_align if c_i in [1, 2, 4] else left_align
        c.border = thin_border

    for idx, co in enumerate(cos):
        curr_r = co_start_r + 2 + idx
        ws_details.cell(curr_r, 1, value=co.get("num", f"CO{idx+1}")).alignment = center_align
        ws_details.cell(curr_r, 2, value=co.get("code", "")).alignment = center_align
        ws_details.cell(curr_r, 3, value=co.get("statement", "")).alignment = wrap_align
        ws_details.cell(curr_r, 4, value=co.get("bl", "")).alignment = center_align
        for c_i in range(1, 5):
            ws_details.cell(curr_r, c_i).border = thin_border

    ws_details.column_dimensions['A'].width = 16
    ws_details.column_dimensions['B'].width = 20
    ws_details.column_dimensions['C'].width = 75
    ws_details.column_dimensions['D'].width = 24

    # ==========================================
    # SHEET 2: 12 CO-PO Mapping (NBA Criterion 3)
    # ==========================================
    ws_map = wb.create_sheet(title="12 CO-PO Mapping")

    ws_map.cell(1, 1, value=institution).font = bold_font
    ws_map.cell(2, 1, value=dept_name).font = subtitle_font
    ws_map.cell(4, 1, value=f"Academic Year: {academic_year} | Class: {class_name}")
    ws_map.cell(4, 11, value=f"Course Code: {course_code}")
    ws_map.cell(5, 1, value=f"Course Name: {course_name}")
    ws_map.cell(6, 1, value=f"Course Coordinator: {coordinator}")
    ws_map.cell(7, 1, value="Mapping of COs with POs and PSOs (NBA Criterion 3)").font = title_font

    # Build Column Header list: PO1..POn, PSO1..PSOm
    cols = []
    for po in pos:
        num = re.search(r"\d+", po.get("code", ""))
        po_n = num.group(0) if num else po.get("code", "")
        cols.append(f"PO {po_n}")
    for pso in psos:
        num = re.search(r"\d+", pso.get("code", ""))
        pso_n = num.group(0) if num else pso.get("code", "")
        cols.append(f"PSO {pso_n}")

    header_row = 9
    c_lbl = ws_map.cell(header_row, 1, value="CO/PO")
    c_lbl.fill = navy_fill
    c_lbl.font = header_font
    c_lbl.alignment = center_align
    c_lbl.border = thin_border

    for c_i, col_name in enumerate(cols, start=2):
        cell = ws_map.cell(header_row, c_i, value=col_name)
        cell.fill = navy_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    # CO Average header
    co_avg_col = len(cols) + 2
    cell_co_avg = ws_map.cell(header_row, co_avg_col, value="CO Average")
    cell_co_avg.fill = navy_sub_fill
    cell_co_avg.font = header_font
    cell_co_avg.alignment = center_align
    cell_co_avg.border = thin_border

    start_row = 10
    co_keys = [c.get("num", f"CO{i+1}") for i, c in enumerate(cos)]

    for idx, co_key in enumerate(co_keys):
        curr_row = start_row + idx
        num_match = re.search(r"\d+", co_key)
        display_num = int(num_match.group(0)) if num_match else idx + 1

        c_num = ws_map.cell(curr_row, 1, value=display_num)
        c_num.alignment = center_align
        c_num.border = thin_border
        c_num.font = bold_font

        row_map = matrix_data.get(co_key, {})
        for c_idx, col_name in enumerate(cols, start=2):
            raw_v = row_map.get(col_name, "-")
            if str(raw_v) in ["1", "2", "3"]:
                cell_val = int(raw_v)
            else:
                cell_val = "-"
            cell = ws_map.cell(curr_row, c_idx, value=cell_val)
            cell.alignment = center_align
            cell.border = thin_border

        # Row average formula: =IF(COUNTIF(B10:N10,">0")=0,"-",ROUND(AVERAGEIF(B10:N10,">0"),2))
        first_col_letter = get_column_letter(2)
        last_col_letter = get_column_letter(len(cols) + 1)
        row_formula = f'=IF(COUNTIF({first_col_letter}{curr_row}:{last_col_letter}{curr_row},">0")=0,"-",ROUND(AVERAGEIF({first_col_letter}{curr_row}:{last_col_letter}{curr_row},">0"),2))'
        cell_r_avg = ws_map.cell(curr_row, co_avg_col, value=row_formula)
        cell_r_avg.alignment = center_align
        cell_r_avg.border = thin_border
        cell_r_avg.font = bold_font

    end_co_row = start_row + len(co_keys) - 1
    avg_row = max(16, end_co_row + 2)

    c_avg_lbl = ws_map.cell(avg_row, 1, value="Average")
    c_avg_lbl.font = bold_font
    c_avg_lbl.alignment = center_align
    c_avg_lbl.fill = light_blue_fill
    c_avg_lbl.border = thin_border

    for c_idx, _ in enumerate(cols, start=2):
        col_letter = get_column_letter(c_idx)
        col_formula = f'=IF(COUNTIF({col_letter}{start_row}:{col_letter}{end_co_row},">0")=0,"-",ROUND(AVERAGEIF({col_letter}{start_row}:{col_letter}{end_co_row},">0"),2))'
        avg_cell = ws_map.cell(avg_row, c_idx, value=col_formula)
        avg_cell.font = bold_font
        avg_cell.alignment = center_align
        avg_cell.border = thin_border
        avg_cell.fill = light_blue_fill

    # Overall Matrix average formula in corner
    overall_formula = f'=IF(COUNTIF({first_col_letter}{start_row}:{last_col_letter}{end_co_row},">0")=0,"-",ROUND(AVERAGEIF({first_col_letter}{start_row}:{last_col_letter}{end_co_row},">0"),2))'
    overall_cell = ws_map.cell(avg_row, co_avg_col, value=overall_formula)
    overall_cell.font = bold_font
    overall_cell.alignment = center_align
    overall_cell.border = thin_border
    overall_cell.fill = light_blue_fill

    ws_map.column_dimensions['A'].width = 12
    for c_i in range(2, len(cols) + 3):
        ws_map.column_dimensions[get_column_letter(c_i)].width = 11

    # ==========================================
    # SHEET 3: Mapping Justifications
    # ==========================================
    ws_just = wb.create_sheet(title="Mapping Justifications")

    ws_just.cell(1, 1, value="Course Outcome – Program Outcome Articulation & Justification Matrix").font = title_font
    ws_just.cell(2, 1, value=f"Course: {course_name} ({course_code}) | {dept_name}").font = subtitle_font

    j_headers = ["CO", "Target Outcome", "Mapping Level", "Match %", "Strength", "CO Skill / Topic", "Pedagogical Rationale & Evaluation Methodology", "Review Flag"]
    for c_idx, h_text in enumerate(j_headers, start=1):
        c_cell = ws_just.cell(4, c_idx, value=h_text)
        c_cell.fill = navy_fill
        c_cell.font = header_font
        c_cell.alignment = center_align if c_idx <= 5 or c_idx == 8 else left_align
        c_cell.border = thin_border

    r_cursor = 5
    for co_key in co_keys:
        co_just = justifications.get(co_key, {})
        row_map = matrix_data.get(co_key, {})
        for col_name in cols:
            m_val = row_map.get(col_name, "-")
            j_info = co_just.get(col_name, {})
            if isinstance(j_info, dict):
                reason = j_info.get("reason", "Correlation evaluated from course outcomes.")
                match_pct = j_info.get("match_percentage", 0.0)
                co_topic = j_info.get("co_topic", "Curriculum Topic")
                is_unc = j_info.get("is_uncertain", False)
                review_flag = "⚠️ Review Suggested" if is_unc else "Verified"
            else:
                reason = str(j_info)
                match_pct = 0.0
                co_topic = "Curriculum Topic"
                review_flag = "Verified"

            val_int = 0
            if str(m_val) in ["1", "2", "3"]:
                val_int = int(m_val)

            strength = "No Mapping" if val_int == 0 else ("Low" if val_int == 1 else ("Moderate" if val_int == 2 else "High"))
            pct_str = f"{match_pct}%" if (val_int > 0 or match_pct > 0) else "-"

            ws_just.cell(r_cursor, 1, value=co_key).alignment = center_align
            ws_just.cell(r_cursor, 2, value=col_name).alignment = center_align
            ws_just.cell(r_cursor, 3, value=val_int if val_int > 0 else "-").alignment = center_align
            ws_just.cell(r_cursor, 4, value=pct_str).alignment = center_align
            ws_just.cell(r_cursor, 5, value=strength).alignment = center_align
            ws_just.cell(r_cursor, 6, value=co_topic).alignment = wrap_align
            ws_just.cell(r_cursor, 7, value=reason).alignment = wrap_align
            ws_just.cell(r_cursor, 8, value=review_flag).alignment = center_align

            for c_i in range(1, 9):
                ws_just.cell(r_cursor, c_i).border = thin_border

            r_cursor += 1

    ws_just.column_dimensions['A'].width = 8
    ws_just.column_dimensions['B'].width = 16
    ws_just.column_dimensions['C'].width = 14
    ws_just.column_dimensions['D'].width = 12
    ws_just.column_dimensions['E'].width = 14
    ws_just.column_dimensions['F'].width = 30
    ws_just.column_dimensions['G'].width = 65
    ws_just.column_dimensions['H'].width = 18

    # ==========================================
    # SHEET 4: Department Outcomes (POs / PSOs / WKs)
    # ==========================================
    ws_outcomes = wb.create_sheet(title="Department Outcomes")

    ws_outcomes.cell(1, 1, value=f"{dept_name} – Official Reference Outcomes").font = title_font
    ws_outcomes.cell(2, 1, value=f"Institution: {institution}").font = subtitle_font

    curr_row = 4
    # POs
    ws_outcomes.cell(curr_row, 1, value="Program Outcomes (POs)").font = bold_font
    curr_row += 1
    ws_outcomes.cell(curr_row, 1, value="Code").fill = navy_fill
    ws_outcomes.cell(curr_row, 1).font = header_font
    ws_outcomes.cell(curr_row, 2, value="Title").fill = navy_fill
    ws_outcomes.cell(curr_row, 2).font = header_font
    ws_outcomes.cell(curr_row, 3, value="Statement").fill = navy_fill
    ws_outcomes.cell(curr_row, 3).font = header_font

    for po in pos:
        curr_row += 1
        ws_outcomes.cell(curr_row, 1, value=po.get("code", "")).alignment = center_align
        ws_outcomes.cell(curr_row, 2, value=po.get("title", "")).alignment = left_align
        ws_outcomes.cell(curr_row, 3, value=po.get("desc", "")).alignment = wrap_align
        for c in range(1, 4):
            ws_outcomes.cell(curr_row, c).border = thin_border

    # PSOs
    curr_row += 2
    ws_outcomes.cell(curr_row, 1, value="Program Specific Outcomes (PSOs)").font = bold_font
    curr_row += 1
    ws_outcomes.cell(curr_row, 1, value="Code").fill = navy_sub_fill
    ws_outcomes.cell(curr_row, 1).font = header_font
    ws_outcomes.cell(curr_row, 2, value="Statement").fill = navy_sub_fill
    ws_outcomes.cell(curr_row, 2).font = header_font

    for pso in psos:
        curr_row += 1
        ws_outcomes.cell(curr_row, 1, value=pso.get("code", "")).alignment = center_align
        ws_outcomes.cell(curr_row, 2, value=pso.get("desc", "")).alignment = wrap_align
        for c in range(1, 3):
            ws_outcomes.cell(curr_row, c).border = thin_border

    # WKs
    if wks:
        curr_row += 2
        ws_outcomes.cell(curr_row, 1, value="Washington Accord Knowledge Profiles (WKs)").font = bold_font
        curr_row += 1
        ws_outcomes.cell(curr_row, 1, value="Code").fill = navy_fill
        ws_outcomes.cell(curr_row, 1).font = header_font
        ws_outcomes.cell(curr_row, 2, value="Description").fill = navy_fill
        ws_outcomes.cell(curr_row, 2).font = header_font

        for wk in wks:
            curr_row += 1
            ws_outcomes.cell(curr_row, 1, value=wk.get("code", "")).alignment = center_align
            ws_outcomes.cell(curr_row, 2, value=wk.get("desc", "")).alignment = wrap_align
            for c in range(1, 3):
                ws_outcomes.cell(curr_row, c).border = thin_border

    ws_outcomes.column_dimensions['A'].width = 12
    ws_outcomes.column_dimensions['B'].width = 28
    ws_outcomes.column_dimensions['C'].width = 80

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
