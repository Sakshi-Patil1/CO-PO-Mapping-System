import os
import re
import json
import openpyxl

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STORE_FILE = os.path.join(DATA_DIR, "departments_data.json")
EXCEL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "for project.xlsx")


def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


def load_store():
    ensure_data_dir()
    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading store: {e}")
    return init_store_from_excel()


def save_store(data):
    ensure_data_dir()
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_sheet_by_keyword(wb, keyword):
    kw = keyword.lower().strip()
    for name in wb.sheetnames:
        if kw in name.lower():
            return wb[name]
    return None


def init_store_from_excel():
    """
    Extracts official AIDS department information and initial DSA course
    from 'for project.xlsx' without modifying the original file.
    """
    ensure_data_dir()

    aids_dept = {
        "id": "aids",
        "name": "Department of Artificial Intelligence and Data Science",
        "short_name": "AI & DS",
        "institution": "Sant Dnyaneshwar Shikshan Sanstha's Annasaheb Dange College of Engineering and Technology, Ashta",
        "program": "UG in Artificial Intelligence and Data Science, B Tech (AIDS)",
        "po_statements": [],
        "pso_statements": [],
        "wk_statements": [],
        "peo_statements": [],
        "courses": []
    }

    course_dsa = {
        "id": "dsa-2adpc202",
        "course_name": "Data Structures and Algorithms",
        "course_code": "2ADPC 202",
        "coordinator": "Dr. Asma A. Shaikh",
        "class_name": "SY B Tech",
        "academic_year": "2026-2027",
        "semester": "Odd",
        "hod": "Head of Department",
        "cos": [],
        "saved_matrix": {}
    }

    if os.path.exists(EXCEL_FILE):
        try:
            wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)

            # 1. WKs
            ws_wk = get_sheet_by_keyword(wb, "WK Statements")
            if ws_wk:
                for r in range(1, ws_wk.max_row + 1):
                    k = ws_wk.cell(r, 1).value
                    v = ws_wk.cell(r, 2).value
                    if k and re.match(r"^WK\s*\d+", str(k).strip(), re.IGNORECASE):
                        wk_code = re.sub(r"[^A-Za-z0-9]", "", str(k).strip()).upper()
                        aids_dept["wk_statements"].append({
                            "code": wk_code,
                            "desc": str(v or "").strip()
                        })

            # 2. PEOs
            ws_peo = get_sheet_by_keyword(wb, "PEO Statements")
            if ws_peo:
                for r in range(1, ws_peo.max_row + 1):
                    k = ws_peo.cell(r, 1).value
                    v = ws_peo.cell(r, 2).value
                    if k and re.match(r"^PEO\s*\d+", str(k).strip(), re.IGNORECASE):
                        peo_code = re.sub(r"[^A-Za-z0-9]", "", str(k).strip()).upper()
                        aids_dept["peo_statements"].append({
                            "code": peo_code,
                            "desc": str(v or "").strip()
                        })

            # 3. POs
            ws_po = get_sheet_by_keyword(wb, "PO Statements")
            if ws_po:
                for r in range(1, ws_po.max_row + 1):
                    k = ws_po.cell(r, 1).value
                    v = ws_po.cell(r, 2).value
                    if k and re.match(r"^PO\s*\d+", str(k).strip(), re.IGNORECASE):
                        po_code = re.sub(r"[^A-Za-z0-9]", "", str(k).strip()).upper()
                        full_desc = str(v or "").strip()
                        title = po_code
                        m = re.match(r"(?:PO\d+:?\s*)([^:]+):(.*)", full_desc, re.DOTALL)
                        if m:
                            title = m.group(1).strip()
                            desc = m.group(2).strip()
                        else:
                            desc = full_desc
                        aids_dept["po_statements"].append({
                            "code": po_code,
                            "title": title,
                            "desc": desc,
                            "full_text": full_desc
                        })

            # 4. PSOs
            ws_pso = get_sheet_by_keyword(wb, "PSO Statements")
            if ws_pso:
                for r in range(1, ws_pso.max_row + 1):
                    k = ws_pso.cell(r, 1).value
                    v = ws_pso.cell(r, 2).value
                    if k and re.match(r"^PSO\s*\d+", str(k).strip(), re.IGNORECASE):
                        pso_code = re.sub(r"[^A-Za-z0-9]", "", str(k).strip()).upper()
                        aids_dept["pso_statements"].append({
                            "code": pso_code,
                            "desc": str(v or "").strip()
                        })

            # 5. DSA Course Info & COs
            ws_co = get_sheet_by_keyword(wb, "CO Statements")
            if ws_co:
                for r in range(1, 15):
                    c1 = str(ws_co.cell(r, 1).value or "").strip()
                    c2 = str(ws_co.cell(r, 2).value or "").strip()
                    if "Course Name" in c1 and c2:
                        course_dsa["course_name"] = c2
                    elif "Course Code" in c1 and c2:
                        course_dsa["course_code"] = c2
                    elif "Class" in c1 and c2:
                        course_dsa["class_name"] = c2
                    elif "Academic Year" in c1 and c2:
                        course_dsa["academic_year"] = c2
                    elif "Semester" in c1 and c2:
                        course_dsa["semester"] = c2

                for r in range(14, ws_co.max_row + 1):
                    c_num = ws_co.cell(r, 1).value
                    c_code = ws_co.cell(r, 2).value
                    c_stmt = ws_co.cell(r, 3).value
                    c_bl = ws_co.cell(r, 4).value
                    if c_num and re.match(r"^CO\s*\d+", str(c_num).strip(), re.IGNORECASE):
                        co_num_str = re.sub(r"[^A-Za-z0-9]", "", str(c_num).strip())
                        code_val = str(c_code or "").strip()
                        # Clean prefix if it used 210 instead of course code 202
                        if "210" in code_val and "202" in course_dsa["course_code"]:
                            code_val = code_val.replace("210", "202")
                        course_dsa["cos"].append({
                            "num": co_num_str,
                            "code": code_val,
                            "statement": str(c_stmt or "").strip(),
                            "bl": str(c_bl or "").strip()
                        })
        except Exception as e:
            print(f"Error parsing Excel for initial store: {e}")

    # Fallback POs/PSOs if empty
    if not aids_dept["po_statements"]:
        standard_pos = [
            ("PO1", "Engineering Knowledge", "Apply knowledge of mathematics, natural science, computing, engineering fundamentals and an engineering specialization as specified in WK1 to WK4, respectively, to develop to the solution of complex engineering problems."),
            ("PO2", "Problem Analysis", "Identify, formulate, review research literature and analyze complex engineering problems, reaching substantiated conclusions with consideration for sustainable development. (WK1 to WK4)"),
            ("PO3", "Design/Development of Solutions", "Design creative solutions for complex engineering problems and design/develop systems/components/processes to meet identified needs with consideration for public health and safety, whole-life cost, net zero carbon, culture, society and environment as required. (WK5)"),
            ("PO4", "Conduct Investigations of Complex Problems", "Conduct investigations of complex engineering problems using research-based knowledge, including design of experiments, modelling, analysis & interpretation of data to provide valid conclusions. (WK8)."),
            ("PO5", "Engineering Tool Usage", "Create, select and apply appropriate techniques, resources and modern engineering & IT tools, including prediction and modelling, recognizing their limitations to solve complex engineering problems. (WK2 and WK6)"),
            ("PO6", "The Engineer and The World", "Analyze and evaluate societal and environmental aspects while solving complex engineering problems for its impact on sustainability with reference to the economy, health, safety, legal framework, culture and environment. (WK1, WK5, and WK7)."),
            ("PO7", "Ethics", "Apply ethical principles and commit to professional ethics, human values, diversity and inclusion; adhere to national & international laws. (WK9)"),
            ("PO8", "Individual and Collaborative Teamwork", "Function effectively as an individual and as a member or leader in diverse/multidisciplinary teams."),
            ("PO9", "Communication", "Communicate effectively and inclusively within the engineering community and society at large, such as being able to comprehend and write effective reports and design documentation, make effective presentations considering cultural, language, and learning differences"),
            ("PO10", "Project Management and Finance", "Apply knowledge and understanding of engineering management principles and economic decision-making and apply these to one's own work, as a member and leader in a team, and to manage projects and in multidisciplinary environments."),
            ("PO11", "Life-Long Learning", "Recognize the need for, and have the preparation and ability for i. independent and life-long learning ii. adaptability to new and emerging technologies and iii. critical thinking in the broadest context of technological change. (WK8)")
        ]
        for code, title, desc in standard_pos:
            aids_dept["po_statements"].append({"code": code, "title": title, "desc": desc, "full_text": f"{code}: {title}: {desc}"})

    if not aids_dept["pso_statements"]:
        aids_dept["pso_statements"] = [
            {"code": "PSO1", "desc": "Apply foundational and advanced concepts of Artificial Intelligence to analyze, model, and develop intelligent systems that solve complex real-world problems."},
            {"code": "PSO2", "desc": "Implement Data Science techniques and tools to extract meaningful insights, build predictive models, and support data-driven decision-making across diverse application domains."}
        ]

    if not aids_dept["wk_statements"]:
        wks = [
            ("WK1", "A systematic, theory-based understanding of the natural sciences applicable to the discipline and awareness of relevant social sciences."),
            ("WK2", "Conceptually-based mathematics, numerical analysis, data analysis, statistics and formal aspects of computer and information science to support detailed analysis and modelling applicable to the discipline."),
            ("WK3", "A systematic, theory-based formulation of engineering fundamentals required in the engineering discipline."),
            ("WK4", "Engineering specialist knowledge that provides theoretical frameworks and bodies of knowledge for the accepted practice areas in the engineering discipline; much is at the forefront of the discipline."),
            ("WK5", "Knowledge, including efficient resource use, environmental impacts, whole-life cost, re-use of resources, net zero carbon, and similar concepts, that supports engineering design and operations in a practice area."),
            ("WK6", "Knowledge of engineering practice (technology) in the practice areas in the engineering discipline."),
            ("WK7", "Knowledge of the role of engineering in society and identified issues in engineering practice in the discipline, such as the professional responsibility of an engineer for public safety and sustainable development."),
            ("WK8", "Engagement with selected knowledge in the current research literature on the discipline, awareness of the power of critical thinking, and creative approaches to evaluate emerging issues.")
        ]
        for code, desc in wks:
            aids_dept["wk_statements"].append({"code": code, "desc": desc})

    if not course_dsa["cos"]:
        course_dsa["cos"] = [
            {"num": "CO1", "code": "2ADPC202_1", "statement": "Explain the fundamental concepts of data structures and algorithms in terms of time and space complexity", "bl": "Level 2 (Understand)"},
            {"num": "CO2", "code": "2ADPC202_2", "statement": "Implement linear data structures by performing insertion, deletion, searching, and traversal operations.", "bl": "Level 3 (Apply)"},
            {"num": "CO3", "code": "2ADPC202_3", "statement": "Demonstrate the representation and traversal techniques of non-linear data structures.", "bl": "Level 3 (Apply)"},
            {"num": "CO4", "code": "2ADPC202_4", "statement": "Apply appropriate searching, sorting, and hashing techniques to solve computational problems and analyze their efficiency.", "bl": "Level 4 (Analyze)"}
        ]

    aids_dept["courses"].append(course_dsa)

    store_data = {
        "departments": {
            "aids": aids_dept
        }
    }

    save_store(store_data)
    return store_data


def get_departments_list():
    data = load_store()
    result = []
    for dept_id, dept in data.get("departments", {}).items():
        result.append({
            "id": dept_id,
            "name": dept.get("name", dept_id),
            "short_name": dept.get("short_name", dept_id.upper()),
            "institution": dept.get("institution", ""),
            "program": dept.get("program", ""),
            "course_count": len(dept.get("courses", [])),
            "po_count": len(dept.get("po_statements", [])),
            "pso_count": len(dept.get("pso_statements", [])),
            "wk_count": len(dept.get("wk_statements", []))
        })
    return result


def get_department(dept_id):
    data = load_store()
    return data.get("departments", {}).get(dept_id)


def add_department(dept_payload):
    data = load_store()
    dept_id = dept_payload.get("id") or re.sub(r"[^a-z0-9]", "", dept_payload.get("name", "").lower()[:8])
    if not dept_id:
        dept_id = f"dept_{len(data['departments']) + 1}"

    # Default POs/WKs if not provided
    po_list = dept_payload.get("po_statements") or []
    if not po_list:
        standard_pos = [
            ("PO1", "Engineering Knowledge", "Apply knowledge of mathematics, natural science, computing, engineering fundamentals and an engineering specialization to develop solutions to complex engineering problems."),
            ("PO2", "Problem Analysis", "Identify, formulate, review research literature and analyze complex engineering problems reaching substantiated conclusions."),
            ("PO3", "Design/Development of Solutions", "Design creative solutions for complex engineering problems and design systems/components/processes to meet identified needs."),
            ("PO4", "Conduct Investigations", "Conduct investigations of complex engineering problems using research-based knowledge and design of experiments."),
            ("PO5", "Modern Tool Usage", "Create, select and apply appropriate techniques, resources and modern engineering & IT tools."),
            ("PO6", "The Engineer and Society", "Analyze and evaluate societal and environmental aspects while solving complex engineering problems."),
            ("PO7", "Ethics", "Apply ethical principles and commit to professional ethics, human values, and norms of engineering practice."),
            ("PO8", "Individual and Collaborative Teamwork", "Function effectively as an individual, and as a member or leader in diverse and multidisciplinary teams."),
            ("PO9", "Communication", "Communicate effectively on complex engineering activities with the engineering community and society."),
            ("PO10", "Project Management and Finance", "Demonstrate knowledge and understanding of engineering and management principles."),
            ("PO11", "Life-Long Learning", "Recognize the need for, and have the preparation and ability to engage in independent and life-long learning.")
        ]
        po_list = [{"code": c, "title": t, "desc": d, "full_text": f"{c}: {t}: {d}"} for c, t, d in standard_pos]

    pso_list = dept_payload.get("pso_statements") or [
        {"code": "PSO1", "desc": f"Apply specialized concepts of {dept_payload.get('name', 'the discipline')} to model and analyze systems."},
        {"code": "PSO2", "desc": f"Design and implement practical solutions utilizing modern domain tools and engineering practices."}
    ]

    wk_list = dept_payload.get("wk_statements") or []

    data["departments"][dept_id] = {
        "id": dept_id,
        "name": dept_payload.get("name", "New Department"),
        "short_name": dept_payload.get("short_name", dept_id.upper()),
        "institution": dept_payload.get("institution", "Annasaheb Dange College of Engineering and Technology, Ashta"),
        "program": dept_payload.get("program", f"B Tech in {dept_payload.get('name', '')}"),
        "po_statements": po_list,
        "pso_statements": pso_list,
        "wk_statements": wk_list,
        "peo_statements": dept_payload.get("peo_statements", []),
        "courses": []
    }
    save_store(data)
    return data["departments"][dept_id]


def get_course(dept_id, course_id):
    dept = get_department(dept_id)
    if not dept:
        return None
    for c in dept.get("courses", []):
        if c.get("id") == course_id:
            return c
    return None


def add_course(dept_id, course_payload):
    data = load_store()
    dept = data.get("departments", {}).get(dept_id)
    if not dept:
        raise ValueError(f"Department '{dept_id}' not found.")

    course_name = course_payload.get("course_name", "").strip()
    course_code = course_payload.get("course_code", "").strip()
    coordinator = course_payload.get("coordinator", "").strip()
    cos = course_payload.get("cos", [])

    if not course_name:
        raise ValueError("Course Name is required.")
    if not course_code:
        raise ValueError("Course Code is required.")
    if not cos:
        raise ValueError("At least one Course Outcome (CO) statement is required.")

    # Generate slug ID
    slug_base = re.sub(r"[^a-z0-9]", "", course_code.lower())
    course_id = f"course-{slug_base}"
    counter = 1
    existing_ids = {c["id"] for c in dept.get("courses", [])}
    while course_id in existing_ids:
        course_id = f"course-{slug_base}-{counter}"
        counter += 1

    new_course = {
        "id": course_id,
        "course_name": course_name,
        "course_code": course_code,
        "coordinator": coordinator or "Faculty In-Charge",
        "class_name": course_payload.get("class_name", "SY B Tech"),
        "academic_year": course_payload.get("academic_year", "2026-2027"),
        "semester": course_payload.get("semester", "Odd"),
        "hod": course_payload.get("hod", "Head of Department"),
        "cos": cos,
        "saved_matrix": {}
    }

    dept["courses"].append(new_course)
    save_store(data)
    return new_course


def save_course_matrix(dept_id, course_id, matrix_data):
    data = load_store()
    dept = data.get("departments", {}).get(dept_id)
    if not dept:
        raise ValueError(f"Department '{dept_id}' not found.")
    for c in dept.get("courses", []):
        if c.get("id") == course_id:
            c["saved_matrix"] = matrix_data
            save_store(data)
            return True
    return False
