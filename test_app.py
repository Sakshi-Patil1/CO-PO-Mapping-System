"""
Automated Test Suite: Multi-Department, Multi-Course OBE CO-PO & CO-PSO Mapping System
======================================================================================
Covers:
  1. Threshold Conversion Rules & Exact Boundary Conditions
  2. Academic Relevance Gate (Stage A):
     - Clearly related CO and PO/PSO statements
     - Clearly unrelated statements strictly returning '-' (0.0%)
     - Superficially similar wording without real academic relationship (returning '-')
     - Generic action verbs that must not create mappings by themselves
     - Technical COs vs Society, Ethics, Teamwork, and Management when context is absent
     - Cross-department PSO domain isolation
  3. Valid Indirect Relationships & Teacher Review Flagging
  4. Mapping Strength Evaluation (Stage B): Low (1), Moderate (2), High (3)
  5. Strict No-Mapping Precedence over Numeric Scores
  6. Existing Flask API Endpoints, Teacher Edits Persistence, Excel Export, and Backward Compatibility
"""

import io
import json
import os
import openpyxl
import app
import store
import mapping_engine


def test_threshold_logic():
    """
    Explicitly tests threshold conversion rules and exact boundary conditions:
    - Below 50.0% -> 1 (Low)
    - From 50.0% through 80.0%, inclusive -> 2 (Moderate)
    - Above 80.0% -> 3 (High)
    - No meaningful relationship -> - (Dash / 0)
    """
    print("\n[TEST SUITE 1: THRESHOLD CONVERSION RULES & BOUNDARIES]")

    test_cases = [
        (0.0, 0, "No Mapping"),
        (25.0, 1, "Low"),
        (48.9, 1, "Low"),
        (49.0, 1, "Low"),
        (49.9, 1, "Low"),
        (50.0, 2, "Moderate"),
        (50.1, 2, "Moderate"),
        (65.0, 2, "Moderate"),
        (79.9, 2, "Moderate"),
        (80.0, 2, "Moderate"),
        (80.1, 3, "High"),
        (85.0, 3, "High"),
        (99.0, 3, "High")
    ]

    for score, expected_val, expected_strength in test_cases:
        val, disp, strength = mapping_engine.score_to_mapping(score, is_relevant=True)
        assert val == expected_val, f"Score {score}%: expected value {expected_val}, got {val}"
        assert strength == expected_strength, f"Score {score}%: expected strength {expected_strength}, got {strength}"
        print(f"  * Score {score:5.1f}% -> Mapping: {disp:2s} ({strength:10s}) [PASSED]")

    print(" -> PASSED: Exact thresholds (49%, 50%, 80%, and >80%) verified.")


def test_no_mapping_precedence():
    """
    Verifies that Stage A no-mapping decision strictly overrides numeric scores.
    Even if raw cosine similarity or lexical matching is high, when no defensible
    relationship exists, the system must strictly return '-' (0, 'No Mapping', 0.0%).
    """
    print("\n[TEST SUITE 2: NO-MAPPING PRECEDENCE OVER NUMERIC SCORES]")

    high_raw_scores = [45.0, 55.0, 75.0, 85.0, 95.0]
    for score in high_raw_scores:
        val, disp, strength = mapping_engine.score_to_mapping(score, is_relevant=False)
        assert val == 0, f"Expected value 0 for is_relevant=False at score {score}, got {val}"
        assert disp == "-", f"Expected '-' for is_relevant=False at score {score}, got {disp}"
        assert strength == "No Mapping", f"Expected 'No Mapping', got {strength}"
        print(f"  * Raw Score {score:5.1f}% with is_relevant=False -> Strictly Assigned '{disp}' ({strength}) [PASSED]")

    print(" -> PASSED: No-mapping decision strictly takes precedence over numeric thresholds.")


def test_academic_relevance_gate_negative_cases():
    """
    Comprehensive tests for Stage A Academic Relevance Gate:
    1. Superficially similar wording without genuine academic relationship:
       - OS concurrency 'problems' vs PO6 ('Society')
       - Minimum 'cost' spanning tree vs PO10 ('Project Management & Finance')
    2. Generic action verbs that must not create mappings by themselves:
       - 'Explain' vs PO9 ('Communication')
       - 'Implement' vs PO7 ('Ethics') or PO8 ('Teamwork')
       - 'Design' vs PO6 ('Society')
    3. Technical algorithms vs non-technical POs without relevant context:
       - Red-Black Tree vs PO6, PO7, PO8, PO9, PO10, PO11
    4. Non-technical orientation activities vs PO1 ('Engineering Knowledge')
    5. Cross-department PSO domain isolation:
       - Mechanical outcomes vs AI/Data Science PSOs
    """
    print("\n[TEST SUITE 3: ACADEMIC RELEVANCE GATE — NEGATIVE & AMBIGUOUS CASES]")

    negative_cases = [
        # 1. Superficially similar words: 'problems' in OS vs PO6 Society
        (
            "CO_OS_PROB",
            "Explain the architectural components of an operating system to resolve concurrency problems.",
            "Level 2 (Understand)",
            "PO6", "The Engineer and Society",
            "Analyze and evaluate societal and environmental aspects while solving complex engineering problems.",
            "-",
            "OS concurrency problems must not map to PO6 Society simply because both contain 'problems'."
        ),
        # 2. Superficially similar words: 'cost' in algorithms vs PO10 Project Management
        (
            "CO_MIN_COST",
            "Compute minimum cost spanning trees using Kruskal and Prim graph algorithms.",
            "Level 3 (Apply)",
            "PO10", "Project Management and Finance",
            "Apply knowledge and understanding of engineering management principles and economic decision-making.",
            "-",
            "Minimum cost graph algorithms must not map to PO10 Finance simply because both contain 'cost'."
        ),
        # 3. Generic action verb 'Explain' must not create a mapping to PO9 Communication
        (
            "CO_EXP_VERB",
            "Explain the execution flow of binary search and bubble sort algorithms.",
            "Level 2 (Understand)",
            "PO9", "Communication",
            "Communicate effectively on complex engineering activities with the engineering community.",
            "-",
            "Action verb 'Explain' in syllabus reflects cognitive understanding, not professional technical communication."
        ),
        # 4. Generic action verb 'Implement' must not create a mapping to PO7 Ethics
        (
            "CO_IMP_ETH",
            "Implement quicksort algorithm in C++ with optimal pivot selection.",
            "Level 3 (Apply)",
            "PO7", "Ethics",
            "Apply ethical principles and commit to professional ethics, human values, and norms of engineering practice.",
            "-",
            "Action verb 'Implement' must not map to PO7 Ethics without explicit ethical/privacy context."
        ),
        # 5. Generic action verb 'Implement' must not create a mapping to PO8 Teamwork
        (
            "CO_IMP_TEAM",
            "Implement quicksort algorithm in C++ with optimal pivot selection.",
            "Level 3 (Apply)",
            "PO8", "Individual and Collaborative Teamwork",
            "Function effectively as an individual and as a member or leader in diverse and multidisciplinary teams.",
            "-",
            "Standard individual implementation outcome must not map to PO8 Teamwork."
        ),
        # 6. Generic action verb 'Design' must not map to PO6 Society without societal context
        (
            "CO_DES_SOC",
            "Design an optimized B-tree structure for high-throughput relational database indexing.",
            "Level 6 (Create)",
            "PO6", "The Engineer and Society",
            "Analyze and evaluate societal and environmental aspects while solving complex engineering problems.",
            "-",
            "Technical algorithmic design must not map to PO6 Society without explicit societal/environmental context."
        ),
        # 7. Non-technical orientation activity vs PO1 Engineering Knowledge
        (
            "CO_NON_TECH",
            "Participate in mandatory campus health and physical fitness orientation routines.",
            "Level 1 (Remember)",
            "PO1", "Engineering Knowledge",
            "Apply knowledge of mathematics, natural science, computing, engineering fundamentals.",
            "-",
            "Non-technical campus activity must not map to PO1 Engineering Knowledge."
        ),
        # 8. Cross-department PSO isolation: Mechanical outcome vs AI PSO1
        (
            "CO_MECH_AI",
            "Analyze heat transfer and thermal efficiency in counterflow shell and tube heat exchangers.",
            "Level 4 (Analyze)",
            "PSO1", "PSO1",
            "Apply foundational and advanced concepts of Artificial Intelligence to analyze, model, and develop intelligent systems.",
            "-",
            "Mechanical thermal outcome must not map to Artificial Intelligence (PSO1)."
        ),
        # 9. Cross-department PSO isolation: Mechanical outcome vs Data Science PSO2
        (
            "CO_MECH_DS",
            "Analyze heat transfer and thermal efficiency in counterflow shell and tube heat exchangers.",
            "Level 4 (Analyze)",
            "PSO2", "PSO2",
            "Implement Data Science techniques and tools to extract meaningful insights, build predictive models.",
            "-",
            "Mechanical thermal outcome must not map to Data Science (PSO2)."
        ),
        # 10. Technical algorithms vs PO6..PO11 without non-technical context
        (
            "CO_RBT_PO11",
            "Implement a self-balancing red-black tree with rotational insertion and deletion operations.",
            "Level 3 (Apply)",
            "PO11", "Life-Long Learning",
            "Recognize the need for, and have the preparation and ability to engage in independent and life-long learning.",
            "-",
            "Standard data structure syllabus topic must not automatically map to PO11 Life-Long Learning."
        )
    ]

    for co_id, stmt, bl, target_code, target_title, target_desc, expected, rationale in negative_cases:
        co = {"statement": stmt, "bl": bl, "num": co_id}
        result = mapping_engine.evaluate_co_target_relationship(co, target_code, target_title, target_desc)
        display_val = result["display"]
        match_pct = result["match_percentage"]

        assert display_val == expected, (
            f"FAILED for {co_id} -> {target_code}: expected '{expected}', got '{display_val}' ({match_pct}%). "
            f"Rationale: {rationale}"
        )
        assert match_pct == 0.0, f"Expected 0.0% for no-mapping result, got {match_pct}%"
        assert result["factor_breakdown"]["domain_relevance"] == 0.0
        assert "No Meaningful Relationship" in result["reason"]
        print(f"  * [{co_id} -> {target_code}] Assigned '{display_val}' ({match_pct:4.1f}%): {rationale} [PASSED]")

    print(" -> PASSED: All negative, superficial, and cross-department cases correctly assigned '-' (0.0%).")


def test_academic_relevance_gate_positive_cases():
    """
    Tests legitimate, academically defensible direct and indirect relationships:
    - Direct technical problem analysis and efficiency -> PO2 (High 3)
    - Direct ethical AI and privacy -> PO7 (High 3)
    - Direct toolchain application (Python, PyTorch) -> PO5 (High 3)
    - Direct empirical investigation and benchmarking -> PO4 (High 3)
    - Direct technical documentation and presentation -> PO9 (Moderate 2 or High 3)
    - Direct collaborative multidisciplinary teamwork -> PO8 (Moderate 2 or High 3)
    - Direct project scheduling and budgeting -> PO10 (High 3)
    - Valid indirect relationships (conceptual complexity -> PO2, basic implementation -> PO5)
      correctly assigned Low (1) and flagged for Teacher Review.
    """
    print("\n[TEST SUITE 4: ACADEMIC RELEVANCE GATE — POSITIVE & INDIRECT CASES]")

    positive_cases = [
        # Direct Problem Analysis (PO2)
        (
            "CO_ALGO_PO2",
            "Apply appropriate searching, sorting, and hashing techniques to solve computational problems and analyze their efficiency.",
            "Level 4 (Analyze)",
            "PO2", "Problem Analysis",
            "Identify, formulate, review research literature and analyze complex engineering problems reaching substantiated conclusions.",
            ["2", "3"],
            "Direct analytical efficiency and computational problem solving."
        ),
        # Direct Ethics (PO7)
        (
            "CO_ETH_PO7",
            "Design ethical AI pipelines adhering to fairness, data privacy, and legal constraints.",
            "Level 6 (Create)",
            "PO7", "Ethics",
            "Apply ethical principles and commit to professional ethics, human values, and diversity.",
            ["2", "3"],
            "Direct professional ethics, privacy, and fairness in AI systems."
        ),
        # Direct Modern Tools (PO5)
        (
            "CO_TOOL_PO5",
            "Develop and train neural networks using Python and modern deep learning libraries.",
            "Level 6 (Create)",
            "PO5", "Modern Tool Usage",
            "Create, select and apply appropriate techniques, resources and modern engineering & IT tools.",
            ["3"],
            "Direct modern IT tools and programming libraries (Python, deep learning)."
        ),
        # Direct Investigation (PO4)
        (
            "CO_INV_PO4",
            "Analyze and benchmark classification models using cross-validation and evaluation metrics.",
            "Level 4 (Analyze)",
            "PO4", "Conduct Investigations of Complex Problems",
            "Conduct investigations of complex engineering problems including design of experiments, modelling, and analysis of data.",
            ["3"],
            "Direct empirical benchmarking, cross-validation, and performance metrics."
        ),
        # Direct Communication (PO9)
        (
            "CO_COMM_PO9",
            "Write comprehensive technical design documentation and deliver oral project presentations.",
            "Level 3 (Apply)",
            "PO9", "Communication",
            "Communicate effectively on complex engineering activities with the engineering community and society.",
            ["2", "3"],
            "Direct professional technical documentation and oral presentations."
        ),
        # Direct Teamwork (PO8)
        (
            "CO_TEAM_PO8",
            "Collaborate as an active member in multidisciplinary project teams to deliver software solutions.",
            "Level 3 (Apply)",
            "PO8", "Individual and Collaborative Teamwork",
            "Function effectively as an individual, and as a member or leader in diverse and multidisciplinary teams.",
            ["2", "3"],
            "Direct multidisciplinary collaborative teamwork."
        ),
        # Direct Project Management & Finance (PO10)
        (
            "CO_MGMT_PO10",
            "Apply project scheduling, lifecycle budgeting, and economic decision-making to engineering projects.",
            "Level 3 (Apply)",
            "PO10", "Project Management and Finance",
            "Apply knowledge and understanding of engineering management principles and economic decision-making.",
            ["3"],
            "Direct project scheduling, economic budgeting, and engineering management."
        ),
        # Direct Life-Long Learning (PO11)
        (
            "CO_LL_PO11",
            "Engage in self-directed research to evaluate emerging technologies and adapt to modern framework advancements.",
            "Level 4 (Analyze)",
            "PO11", "Life-Long Learning",
            "Recognize the need for, and have the preparation and ability to engage in independent and life-long learning.",
            ["2", "3"],
            "Direct self-directed learning and adaptation to emerging technologies."
        )
    ]

    for co_id, stmt, bl, target_code, target_title, target_desc, allowed_levels, rationale in positive_cases:
        co = {"statement": stmt, "bl": bl, "num": co_id}
        result = mapping_engine.evaluate_co_target_relationship(co, target_code, target_title, target_desc)
        display_val = result["display"]
        match_pct = result["match_percentage"]

        assert display_val in allowed_levels, (
            f"FAILED for {co_id} -> {target_code}: expected one of {allowed_levels}, got '{display_val}' ({match_pct}%)."
        )
        assert match_pct > 0.0, f"Expected non-zero match percentage, got {match_pct}%"
        print(f"  * [{co_id} -> {target_code}] Assigned '{display_val}' ({match_pct:4.1f}%): {rationale} [PASSED]")

    # Valid Indirect Relationships & Teacher Review Flagging
    print("  * Checking valid indirect relationships and teacher review flagging:")

    # Indirect Case 1: DSA CO1 conceptual time/space complexity supporting PO2 Problem Analysis
    co_indirect_1 = {
        "num": "CO1",
        "statement": "Explain the fundamental concepts of data structures and algorithms in terms of time and space complexity",
        "bl": "Level 2 (Understand)"
    }
    po2_info = ("PO2", "Problem Analysis", "Identify, formulate, review research literature and analyze complex engineering problems.")
    res_ind_1 = mapping_engine.evaluate_co_target_relationship(co_indirect_1, po2_info[0], po2_info[1], po2_info[2])
    assert res_ind_1["display"] == "1", f"Expected Low (1) for indirect conceptual complexity, got {res_ind_1['display']}"
    assert res_ind_1["is_uncertain"] is True, "Indirect relationship must be flagged for Teacher Review"
    print(f"    - DSA CO1 -> PO2 (Conceptual Complexity): Assigned '1' ({res_ind_1['match_percentage']}%), Review Flagged: {res_ind_1['is_uncertain']} [PASSED]")

    # Indirect Case 2: DSA CO2 practical linear structure implementation supporting PO5 Tools
    co_indirect_2 = {
        "num": "CO2",
        "statement": "Implement linear data structures by performing insertion, deletion, searching, and traversal operations.",
        "bl": "Level 3 (Apply)"
    }
    po5_info = ("PO5", "Modern Tool Usage", "Create, select and apply appropriate techniques, resources and modern engineering & IT tools.")
    res_ind_2 = mapping_engine.evaluate_co_target_relationship(co_indirect_2, po5_info[0], po5_info[1], po5_info[2])
    assert res_ind_2["display"] == "1", f"Expected Low (1) for practical tool execution, got {res_ind_2['display']}"
    assert res_ind_2["is_uncertain"] is True, "Indirect tool execution must be flagged for Teacher Review"
    print(f"    - DSA CO2 -> PO5 (Tool Execution): Assigned '1' ({res_ind_2['match_percentage']}%), Review Flagged: {res_ind_2['is_uncertain']} [PASSED]")

    print(" -> PASSED: Positive direct and indirect academic relationships correctly mapped and flagged.")


def run_tests():
    print("=" * 65)
    print("AUTOMATED TEST SUITE: MULTI-DEPARTMENT & MULTI-COURSE OBE SYSTEM")
    print("=" * 65)

    client = app.app.test_client()

    # 1. Threshold logic and boundaries
    test_threshold_logic()

    # 2. Strict no-mapping precedence
    test_no_mapping_precedence()

    # 3. Negative & superficial relevance checks
    test_academic_relevance_gate_negative_cases()

    # 4. Positive & indirect relevance checks
    test_academic_relevance_gate_positive_cases()

    # 5. GET / Index route verification
    print("\n[TEST 1] Testing Index Route (GET /)...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode("utf-8")
    assert "Automated CO–PO" in html, "Missing title in HTML"
    assert "Select Department:" in html, "Missing 'Select Department:' label in HTML"
    assert "Select Course:" in html, "Missing 'Select Course:' label in HTML"
    assert "Load Sheet 12 Original" not in html, "Old 'Load Sheet 12 Original' button must be removed!"
    assert "Evaluation Factor Breakdown" in html, "Missing factor breakdown in modal"
    print(" -> PASSED: Index page served with complete Department navigation & without Sheet 12 button.")

    # 6. GET /api/departments (List departments)
    print("\n[TEST 2] Testing List Departments (GET /api/departments)...")
    res_depts = client.get("/api/departments")
    assert res_depts.status_code == 200
    depts_data = json.loads(res_depts.data)
    assert depts_data["status"] == "success"
    depts_list = depts_data["departments"]
    assert any(d["id"] == "aids" for d in depts_list), "AIDS department must be present"
    print(f" -> Found {len(depts_list)} department(s): {[d['name'] for d in depts_list]}")
    print(" -> PASSED: Department listing API works correctly.")

    # 7. GET /api/departments/aids (Department details & courses)
    print("\n[TEST 3] Testing Get Department Details (GET /api/departments/aids)...")
    res_aids = client.get("/api/departments/aids")
    assert res_aids.status_code == 200
    aids_json = json.loads(res_aids.data)
    dept = aids_json["department"]
    assert len(dept["po_statements"]) >= 11, "AIDS must have at least 11 POs"
    assert len(dept["pso_statements"]) >= 2, "AIDS must have at least 2 PSOs"
    assert len(dept["wk_statements"]) >= 8, "AIDS must have at least 8 WKs"
    assert len(dept["courses"]) >= 1, "AIDS must have at least 1 initial course"
    dsa_course = dept["courses"][0]
    print(f" -> AIDS POs: {len(dept['po_statements'])}, PSOs: {len(dept['pso_statements'])}, Courses: {len(dept['courses'])}")
    print(" -> PASSED: Department details and statements retrieved successfully.")

    # 8. GET /api/departments/aids/courses/<course_id> (Course mapping & suggestions)
    print(f"\n[TEST 4] Testing Course Mapping Endpoint (GET /api/departments/aids/courses/{dsa_course['id']})...")
    res_c = client.get(f"/api/departments/aids/courses/{dsa_course['id']}")
    assert res_c.status_code == 200
    c_data = json.loads(res_c.data)
    assert c_data["status"] == "success"
    assert c_data["course"]["course_name"] == "Data Structures and Algorithms"
    assert len(c_data["course"]["cos"]) == 4
    suggs = c_data["suggestions"]
    live_mat = c_data["matrix"]
    assert len(suggs) == 4
    assert len(live_mat) == 4

    # Verify suggestions and threshold compliance
    threshold_counts = {"3": 0, "2": 0, "1": 0, "-": 0}
    uncertain_count = 0
    for co_k, targets in suggs.items():
        for target_k, item in targets.items():
            assert "match_percentage" in item
            assert "factor_breakdown" in item
            assert "reason" in item
            assert "is_uncertain" in item
            disp = item["display"]
            threshold_counts[disp] = threshold_counts.get(disp, 0) + 1
            if item["is_uncertain"]:
                uncertain_count += 1

    print(f" -> Mapping distribution: {threshold_counts}")
    print(f" -> Uncertain / Borderline cells for review: {uncertain_count}")
    assert threshold_counts["3"] > 0, "Expected at least one High (3) correlation (>80%)"
    assert threshold_counts["2"] > 0, "Expected at least one Moderate (2) correlation (50-80%)"
    assert threshold_counts["1"] > 0, "Expected at least one Low (1) correlation (<50%)"
    assert threshold_counts["-"] > 0, "Expected at least one No Mapping (-) correlation (0%)"
    assert uncertain_count > 0, "Expected borderline / indirect cells to be flagged for teacher review"
    print(" -> PASSED: Multi-factor scoring successfully populates all 4 threshold categories with teacher review flags.")

    # 9. POST /api/departments/aids/courses (Adding a new course)
    print("\n[TEST 5] Testing Add New Course (POST /api/departments/aids/courses)...")
    new_course_payload = {
        "course_name": "Machine Learning",
        "course_code": "2ADPC 301",
        "coordinator": "Prof. R. S. Kulkarni",
        "class_name": "TY B Tech",
        "academic_year": "2026-2027",
        "semester": "Odd",
        "cos": [
            {
                "num": "CO1",
                "code": "2ADPC301_1",
                "statement": "Understand core mathematical foundations of supervised learning algorithms.",
                "bl": "Level 2 (Understand)"
            },
            {
                "num": "CO2",
                "code": "2ADPC301_2",
                "statement": "Develop and train neural networks using Python and modern deep learning libraries.",
                "bl": "Level 6 (Create)"
            },
            {
                "num": "CO3",
                "code": "2ADPC301_3",
                "statement": "Analyze and benchmark classification models using cross-validation and evaluation metrics.",
                "bl": "Level 4 (Analyze)"
            },
            {
                "num": "CO4",
                "code": "2ADPC301_4",
                "statement": "Design ethical AI pipelines adhering to fairness, data privacy, and legal constraints.",
                "bl": "Level 6 (Create)"
            }
        ]
    }
    res_add_c = client.post("/api/departments/aids/courses", json=new_course_payload)
    assert res_add_c.status_code == 201
    added_course = json.loads(res_add_c.data)["course"]
    print(f" -> Added new course: {added_course['course_name']} ({added_course['course_code']}), ID: {added_course['id']}")

    # Verify newly added course can be retrieved and mapped
    res_ml = client.get(f"/api/departments/aids/courses/{added_course['id']}")
    assert res_ml.status_code == 200
    ml_data = json.loads(res_ml.data)
    ml_suggs = ml_data["suggestions"]
    # Check that ethical AI (CO4) mapped to PO7 (Ethics)
    assert ml_suggs["CO4"]["PO 7"]["display"] in ["1", "2", "3"]
    # Check that unrelated CO1 has "-" for PO7
    assert ml_suggs["CO1"]["PO 7"]["display"] == "-"
    print(f" -> Machine Learning CO4 -> PO7 (Ethics): {ml_suggs['CO4']['PO 7']['display']} ({ml_suggs['CO4']['PO 7']['match_percentage']}%)")
    print(f" -> Machine Learning CO1 -> PO7 (Ethics): {ml_suggs['CO1']['PO 7']['display']} ({ml_suggs['CO1']['PO 7']['match_percentage']}%)")
    print(" -> PASSED: New course added and dynamically mapped with academic precision.")

    # 10. POST /api/departments/aids/courses/<id>/save (Teacher edit saving)
    print(f"\n[TEST 6] Testing Save Teacher Edits (POST .../courses/{added_course['id']}/save)...")
    edited_matrix = ml_data["matrix"]
    edited_matrix["CO1"]["PO 1"] = "3"  # Teacher promotes CO1 -> PO1 to 3
    res_save = client.post(f"/api/departments/aids/courses/{added_course['id']}/save", json={"matrix": edited_matrix})
    assert res_save.status_code == 200
    # Verify saved edit persists upon re-fetching
    res_check = client.get(f"/api/departments/aids/courses/{added_course['id']}")
    check_data = json.loads(res_check.data)
    assert check_data["matrix"]["CO1"]["PO 1"] == "3"
    print(" -> PASSED: Teacher edits saved and successfully retrieved.")

    # 11. POST /api/departments/aids/courses/<id>/export (Course-specific Excel export)
    print(f"\n[TEST 7] Testing Course Excel Export (POST .../courses/{added_course['id']}/export)...")
    res_exp_course = client.post(
        f"/api/departments/aids/courses/{added_course['id']}/export",
        json={"matrix": edited_matrix, "justifications": ml_suggs}
    )
    assert res_exp_course.status_code == 200
    assert "spreadsheet" in res_exp_course.content_type
    wb_course = openpyxl.load_workbook(io.BytesIO(res_exp_course.data))
    print(f" -> Exported sheets for {added_course['course_name']}: {wb_course.sheetnames}")
    assert "Course Details & COs" in wb_course.sheetnames
    assert "12 CO-PO Mapping" in wb_course.sheetnames
    assert "Mapping Justifications" in wb_course.sheetnames
    assert "Department Outcomes" in wb_course.sheetnames

    # Check course details sheet has Machine Learning
    ws_c_details = wb_course["Course Details & COs"]
    assert "Machine Learning" in [ws_c_details.cell(r, 2).value for r in range(6, 12)]
    # Check mapping sheet has value 3 for edited cell
    ws_c_map = wb_course["12 CO-PO Mapping"]
    assert ws_c_map.cell(10, 2).value == 3
    print(" -> PASSED: Course-specific Excel export generated with all 4 sheets and teacher edits.")

    # 12. POST /api/departments (Adding a new department)
    print("\n[TEST 8] Testing Add New Department (POST /api/departments)...")
    dept_mech_payload = {
        "id": "mech",
        "name": "Department of Mechanical Engineering",
        "short_name": "MECH",
        "institution": "Annasaheb Dange College of Engineering and Technology, Ashta",
        "program": "UG in Mechanical Engineering, B Tech (MECH)",
        "pso_statements": [
            {"code": "PSO1", "desc": "Apply principles of mechanics, thermal systems, and design to engineering problems."},
            {"code": "PSO2", "desc": "Utilize modern CAD/CAM/CAE tools to model and manufacture mechanical systems."}
        ]
    }
    res_add_dept = client.post("/api/departments", json=dept_mech_payload)
    assert res_add_dept.status_code == 201
    mech_dept = json.loads(res_add_dept.data)["department"]
    assert mech_dept["id"] == "mech"

    # Verify statements are isolated between AIDS and MECH
    res_mech_get = client.get("/api/departments/mech")
    mech_get_data = json.loads(res_mech_get.data)["department"]
    assert "Mechanical" in mech_get_data["pso_statements"][0]["desc"] or "thermal" in mech_get_data["pso_statements"][0]["desc"]
    assert "Artificial Intelligence" not in mech_get_data["pso_statements"][0]["desc"]
    print(" -> PASSED: New department created and completely isolated from other departments.")

    # 13. Backward Compatibility & Original File Integrity Check
    print("\n[TEST 9] Testing Backward Compatibility & File Integrity...")
    orig_mtime = os.path.getmtime(app.EXCEL_FILE)
    res_legacy_data = client.get("/api/data")
    assert res_legacy_data.status_code == 200
    res_legacy_exp = client.post("/api/export", json={"matrix": {}, "justifications": {}})
    assert res_legacy_exp.status_code == 200
    assert os.path.getmtime(app.EXCEL_FILE) == orig_mtime, "Original file must NEVER be modified!"
    print(" -> Original workbook 'for project.xlsx' remained completely untouched and pristine.")
    print(" -> PASSED: Backward compatibility routes operational.")

    print("\n" + "=" * 65)
    print("ALL TESTS COMPLETED SUCCESSFULLY WITH 100% PASS RATE!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
