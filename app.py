import os
import io
import re
import json
import openpyxl
from flask import Flask, render_template, jsonify, request, send_file
import store
import mapping_engine
from excel_export import create_course_export_workbook

app = Flask(__name__)

EXCEL_FILE = "for project.xlsx"

# Ensure data store is initialized
store.load_store()


def parse_excel_for_course(file_stream_or_path):
    """
    Parses course metadata and CO statements from an uploaded Excel file.
    Supports ADCET OBE format as well as standard tables.
    """
    wb = openpyxl.load_workbook(file_stream_or_path, data_only=True)

    ws_co = None
    for name in wb.sheetnames:
        if "co" in name.lower() and "statement" in name.lower():
            ws_co = wb[name]
            break
    if not ws_co:
        for name in wb.sheetnames:
            if "co" in name.lower():
                ws_co = wb[name]
                break
    if not ws_co:
        ws_co = wb.active

    course_data = {
        "course_name": "",
        "course_code": "",
        "coordinator": "",
        "class_name": "SY B Tech",
        "academic_year": "2026-2027",
        "semester": "Odd",
        "hod": "Head of Department",
        "cos": []
    }

    # Extract metadata fields
    for r in range(1, min(25, ws_co.max_row + 1)):
        for c in range(1, min(6, ws_co.max_column + 1)):
            val = str(ws_co.cell(r, c).value or "").strip()
            val_next = str(ws_co.cell(r, c + 1).value or "").strip() if c + 1 <= ws_co.max_column else ""
            if "Course Name" in val and val_next:
                course_data["course_name"] = val_next
            elif "Course Code" in val and val_next:
                course_data["course_code"] = val_next
            elif "Class" in val and val_next:
                course_data["class_name"] = val_next
            elif "Academic Year" in val and val_next:
                course_data["academic_year"] = val_next
            elif "Semester" in val and val_next:
                course_data["semester"] = val_next
            elif ("Coordinator" in val or "Course Coordinator" in val) and val_next:
                course_data["coordinator"] = val_next

    # Extract CO Statements
    for r in range(1, ws_co.max_row + 1):
        c1 = str(ws_co.cell(r, 1).value or "").strip()
        c2 = str(ws_co.cell(r, 2).value or "").strip()
        c3 = str(ws_co.cell(r, 3).value or "").strip()
        c4 = str(ws_co.cell(r, 4).value or "").strip()

        m = re.match(r"^CO\s*(\d+)", c1, re.IGNORECASE)
        if m:
            co_num = f"CO{m.group(1)}"
            code = c2
            stmt = c3
            bl = c4
            if stmt:
                course_data["cos"].append({
                    "num": co_num,
                    "code": code or f"{course_data['course_code']}_{m.group(1)}",
                    "statement": stmt,
                    "bl": bl or "Level 2 (Understand)"
                })
        elif c1.isdigit() and int(c1) in range(1, 15) and c3:
            co_num = f"CO{c1}"
            course_data["cos"].append({
                "num": co_num,
                "code": c2 or f"{course_data['course_code']}_{c1}",
                "statement": c3,
                "bl": c4 or "Level 2 (Understand)"
            })

    return course_data


@app.route("/")
def index():
    departments = store.get_departments_list()
    # Default to aids
    default_dept = store.get_department("aids") or (store.get_department(departments[0]["id"]) if departments else None)
    default_course = default_dept["courses"][0] if default_dept and default_dept.get("courses") else None

    suggestions = {}
    if default_dept and default_course:
        suggestions = mapping_engine.generate_course_suggestions(
            default_course.get("cos", []),
            default_dept.get("po_statements", []),
            default_dept.get("pso_statements", [])
        )

    # Note: Reference sheet 12 is deliberately excluded from template rendering
    data = {
        "departments": departments,
        "active_dept": default_dept,
        "active_course": default_course,
        "course_info": default_course,
        "cos": default_course.get("cos", []) if default_course else [],
        "po_statements": default_dept.get("po_statements", []) if default_dept else [],
        "pso_statements": default_dept.get("pso_statements", []) if default_dept else [],
        "wk_statements": default_dept.get("wk_statements", []) if default_dept else [],
        "peo_statements": default_dept.get("peo_statements", []) if default_dept else [],
        "discrepancies": []  # Cleaned / Sheet 12 removed
    }

    return render_template("index.html", data=data, suggestions=suggestions)


# ========================================================
# DEPARTMENT APIS
# ========================================================

@app.route("/api/departments", methods=["GET"])
def api_get_departments():
    try:
        depts = store.get_departments_list()
        return jsonify({"status": "success", "departments": depts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/departments", methods=["POST"])
def api_add_department():
    try:
        payload = request.get_json() or {}
        new_dept = store.add_department(payload)
        return jsonify({"status": "success", "department": new_dept}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/departments/<dept_id>", methods=["GET"])
def api_get_department(dept_id):
    try:
        dept = store.get_department(dept_id)
        if not dept:
            return jsonify({"status": "error", "message": f"Department '{dept_id}' not found"}), 404
        return jsonify({"status": "success", "department": dept})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ========================================================
# COURSE APIS
# ========================================================

@app.route("/api/departments/<dept_id>/courses/<course_id>", methods=["GET"])
def api_get_course(dept_id, course_id):
    try:
        dept = store.get_department(dept_id)
        if not dept:
            return jsonify({"status": "error", "message": f"Department '{dept_id}' not found"}), 404

        course = store.get_course(dept_id, course_id)
        if not course:
            return jsonify({"status": "error", "message": f"Course '{course_id}' not found"}), 404

        cos = course.get("cos", [])
        pos = dept.get("po_statements", [])
        psos = dept.get("pso_statements", [])
        wks = dept.get("wk_statements", [])

        # Generate explainable suggestions
        suggestions = mapping_engine.generate_course_suggestions(cos, pos, psos)

        # Build live matrix (use saved_matrix if teacher already saved edits, otherwise default to suggestions)
        saved = course.get("saved_matrix") or {}
        live_matrix = {}
        for co in cos:
            co_k = co["num"]
            live_matrix[co_k] = {}
            # POs
            for po in pos:
                num = re.search(r"\d+", po["code"])
                po_num = num.group(0) if num else po["code"]
                col_k = f"PO {po_num}"
                if co_k in saved and col_k in saved[co_k]:
                    live_matrix[co_k][col_k] = str(saved[co_k][col_k])
                else:
                    val = suggestions.get(co_k, {}).get(col_k, {}).get("value", 0)
                    live_matrix[co_k][col_k] = "-" if val == 0 else str(val)
            # PSOs
            for pso in psos:
                num = re.search(r"\d+", pso["code"])
                pso_num = num.group(0) if num else pso["code"]
                col_k = f"PSO {pso_num}"
                if co_k in saved and col_k in saved[co_k]:
                    live_matrix[co_k][col_k] = str(saved[co_k][col_k])
                else:
                    val = suggestions.get(co_k, {}).get(col_k, {}).get("value", 0)
                    live_matrix[co_k][col_k] = "-" if val == 0 else str(val)

        return jsonify({
            "status": "success",
            "department": {
                "id": dept["id"],
                "name": dept["name"],
                "short_name": dept.get("short_name", ""),
                "program": dept.get("program", ""),
                "institution": dept.get("institution", "")
            },
            "course": course,
            "po_statements": pos,
            "pso_statements": psos,
            "wk_statements": wks,
            "peo_statements": dept.get("peo_statements", []),
            "suggestions": suggestions,
            "matrix": live_matrix
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/departments/<dept_id>/courses", methods=["POST"])
def api_add_course(dept_id):
    try:
        payload = request.get_json() or {}
        new_course = store.add_course(dept_id, payload)
        return jsonify({"status": "success", "course": new_course}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/parse-course-excel", methods=["POST"])
def api_parse_course_excel():
    """Parses uploaded Excel workbook and extracts course metadata + COs for modal preview."""
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400
        file = request.files["file"]
        if not file.filename.endswith((".xlsx", ".xlsm")):
            return jsonify({"status": "error", "message": "Only Excel files (.xlsx, .xlsm) are supported"}), 400

        parsed = parse_excel_for_course(file.stream)
        return jsonify({"status": "success", "data": parsed})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to parse Excel file: {str(e)}"}), 400


@app.route("/api/departments/<dept_id>/courses/upload", methods=["POST"])
def api_upload_course(dept_id):
    """Directly uploads an Excel file and adds the new course to the department."""
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400
        file = request.files["file"]
        if not file.filename.endswith((".xlsx", ".xlsm")):
            return jsonify({"status": "error", "message": "Only Excel files (.xlsx, .xlsm) are supported"}), 400

        parsed = parse_excel_for_course(file.stream)
        if not parsed.get("course_name"):
            parsed["course_name"] = os.path.splitext(file.filename)[0].replace("_", " ").title()
        if not parsed.get("course_code"):
            parsed["course_code"] = "COURSE 101"
        if not parsed.get("cos"):
            return jsonify({"status": "error", "message": "No Course Outcome (CO) statements found in the uploaded workbook."}), 400

        new_course = store.add_course(dept_id, parsed)
        return jsonify({"status": "success", "course": new_course}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/departments/<dept_id>/courses/<course_id>/save", methods=["POST"])
def api_save_course_matrix(dept_id, course_id):
    try:
        payload = request.get_json() or {}
        matrix_data = payload.get("matrix", {})
        success = store.save_course_matrix(dept_id, course_id, matrix_data)
        if not success:
            return jsonify({"status": "error", "message": "Course not found"}), 404
        return jsonify({"status": "success", "message": "Teacher mapping successfully saved!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/departments/<dept_id>/courses/<course_id>/suggest", methods=["POST"])
def api_suggest_course(dept_id, course_id):
    try:
        dept = store.get_department(dept_id)
        course = store.get_course(dept_id, course_id)
        if not dept or not course:
            return jsonify({"status": "error", "message": "Department or Course not found"}), 404

        suggestions = mapping_engine.generate_course_suggestions(
            course.get("cos", []),
            dept.get("po_statements", []),
            dept.get("pso_statements", [])
        )
        return jsonify({"status": "success", "suggestions": suggestions})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/departments/<dept_id>/courses/<course_id>/export", methods=["POST"])
def api_export_course(dept_id, course_id):
    """
    Exports the specific course's mapping results to a standalone Excel workbook.
    Original workbook is never touched.
    """
    try:
        dept = store.get_department(dept_id)
        course = store.get_course(dept_id, course_id)
        if not dept or not course:
            return jsonify({"status": "error", "message": "Department or Course not found"}), 404

        req_data = request.get_json() or {}
        matrix_data = req_data.get("matrix", course.get("saved_matrix", {}))
        justifications = req_data.get("justifications")

        if not justifications:
            justifications = mapping_engine.generate_course_suggestions(
                course.get("cos", []),
                dept.get("po_statements", []),
                dept.get("pso_statements", [])
            )

        output_stream = create_course_export_workbook(dept, course, matrix_data, justifications)

        clean_code = re.sub(r"[^A-Za-z0-9]", "_", course.get("course_code", "Course"))
        filename = f"CO_PO_Mapping_{clean_code}.xlsx"

        return send_file(
            output_stream,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ========================================================
# BACKWARD COMPATIBILITY ENDPOINTS (For existing tests)
# ========================================================

@app.route("/api/data", methods=["GET"])
def api_data():
    """
    Backward-compatible endpoint providing the active/default course data.
    Sheet 12 reference mapping is removed from dashboard data.
    """
    try:
        dept = store.get_department("aids")
        course = dept["courses"][0] if dept and dept.get("courses") else None

        suggestions = mapping_engine.generate_course_suggestions(
            course.get("cos", []),
            dept.get("po_statements", []),
            dept.get("pso_statements", [])
        )

        course_info = {
            "institution": dept.get("institution", ""),
            "department": dept.get("name", ""),
            "program": dept.get("program", ""),
            "course_name": course.get("course_name", ""),
            "course_code": course.get("course_code", ""),
            "class_name": course.get("class_name", ""),
            "academic_year": course.get("academic_year", ""),
            "semester": course.get("semester", ""),
            "coordinator": course.get("coordinator", ""),
            "hod": course.get("hod", ""),
            "sheet12_course_code": course.get("course_code", "")
        }

        data_payload = {
            "course_info": course_info,
            "wk_statements": dept.get("wk_statements", []),
            "peo_statements": dept.get("peo_statements", []),
            "po_statements": dept.get("po_statements", []),
            "pso_statements": dept.get("pso_statements", []),
            "cos": course.get("cos", []),
            "sheet12_matrix": {},  # Sheet 12 reference mapping removed
            "discrepancies": []
        }

        return jsonify({
            "status": "success",
            "data": data_payload,
            "suggestions": suggestions
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/suggest", methods=["POST"])
def api_suggest():
    try:
        dept = store.get_department("aids")
        course = dept["courses"][0]
        suggestions = mapping_engine.generate_course_suggestions(
            course.get("cos", []),
            dept.get("po_statements", []),
            dept.get("pso_statements", [])
        )
        return jsonify({"status": "success", "suggestions": suggestions})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/export", methods=["POST"])
def api_export():
    """
    Backward-compatible export endpoint for the default course.
    """
    try:
        dept = store.get_department("aids")
        course = dept["courses"][0]
        req_data = request.get_json() or {}
        matrix_data = req_data.get("matrix", {})
        justifications = req_data.get("justifications", {})

        output_stream = create_course_export_workbook(dept, course, matrix_data, justifications)
        return send_file(
            output_stream,
            as_attachment=True,
            download_name="CO_PO_Mapping_Updated.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
