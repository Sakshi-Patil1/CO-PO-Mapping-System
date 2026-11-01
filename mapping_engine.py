"""
Academic Relevance & Mapping Engine for Outcome-Based Education (OBE)
====================================================================
Implements a rigorous, explainable, two-stage evaluation methodology:
  Stage A — Academic Relevance Gate:
    Determines whether a direct or defensible academic relationship exists
    between the Course Outcome (CO) and the target Program Outcome (PO)
    or Program Specific Outcome (PSO). Unrelated or weakly related pairs
    are strictly assigned '-' (No Mapping, 0.0%) regardless of raw lexical scores.
  Stage B — Mapping Strength Evaluation:
    Evaluates correlation strength only for pairs passing Stage A:
      - Domain & Curricular Competency Alignment (40%)
      - Bloom's Action Verb & Cognitive Demand Demand (25%)
      - Substantive Key Phrase / Lexical Overlap (15%)
      - Cosine Semantic Similarity with Academic Filtering (20%)
    Produces standard OBE mapping scale:
      - '-' : No meaningful relationship (0.0%)
      - '1' : Low correlation (< 50.0%)
      - '2' : Moderate correlation (50.0% to 80.0%)
      - '3' : High correlation (> 80.0%)
    Flags ambiguous or borderline cells for essential Teacher Review.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

# Academic stopwords: generic boilerplate terms that inflate lexical matching
# without indicating a specific curricular competency or academic relationship.
STOPWORDS_ACADEMIC = {
    "apply", "applying", "application", "applications",
    "understand", "understanding", "comprehend",
    "explain", "explaining", "explanation", "describe", "describing",
    "demonstrate", "demonstrating", "demonstration",
    "ability", "able", "knowledge", "engineering", "complex",
    "problem", "problems", "solution", "solutions",
    "study", "student", "students", "specified", "respectively",
    "reaching", "reach", "consideration", "required", "appropriate",
    "concept", "concepts", "fundamentals", "discipline", "practice",
    "use", "using", "broadest", "identifying", "identified",
    "review", "various", "different", "provide", "provides",
    "including", "terms", "manner", "based", "relevant", "well",
    "to", "of", "in", "and", "or", "for", "on", "the", "a", "an", "as"
}

# Short technical acronyms that should be preserved during substantive token extraction
SHORT_ALLOWED_TERMS = {"ai", "ml", "it", "ui", "ip", "c", "r", "db", "os"}


def preprocess_text(text):
    """Normalizes text by lowercasing and stripping non-alphanumeric characters."""
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_substantive_tokens(text):
    """Extracts meaningful domain words, filtering out generic academic filler."""
    clean = preprocess_text(text)
    words = clean.split()
    return [w for w in words if w not in STOPWORDS_ACADEMIC and (len(w) > 2 or w in SHORT_ALLOWED_TERMS)]


def extract_bloom_info(co_statement, co_bl=""):
    """
    Extracts Bloom's Revised Taxonomy cognitive level (1 to 6), action verb, and label.
    Preserves teacher's syllabus cognitive declaration while analyzing action verb.
    """
    clean_stmt = preprocess_text(co_statement)
    words = clean_stmt.split()
    first_few = words[:4] if len(words) >= 4 else words
    bl_lower = (co_bl or "").lower()

    # Check explicit BL label first
    explicit_level = None
    if "level 6" in bl_lower or "create" in bl_lower or "design" in bl_lower:
        explicit_level = 6
    elif "level 5" in bl_lower or "evaluate" in bl_lower or "evaluating" in bl_lower:
        explicit_level = 5
    elif "level 4" in bl_lower or "analyze" in bl_lower or "analysis" in bl_lower or "analysing" in bl_lower:
        explicit_level = 4
    elif "level 3" in bl_lower or "apply" in bl_lower or "implement" in bl_lower:
        explicit_level = 3
    elif "level 2" in bl_lower or "understand" in bl_lower or "explain" in bl_lower:
        explicit_level = 2
    elif "level 1" in bl_lower or "remember" in bl_lower or "recall" in bl_lower:
        explicit_level = 1

    verbs_l6 = {"design", "develop", "formulate", "synthesize", "plan", "create", "devise", "architect", "construct"}
    verbs_l5 = {"evaluate", "assess", "validate", "verify", "judge", "critique", "justify", "audit"}
    verbs_l4 = {"analyze", "analyse", "compare", "contrast", "examine", "investigate", "differentiate", "inspect", "profile", "benchmark"}
    verbs_l3 = {"apply", "implement", "demonstrate", "compute", "calculate", "solve", "execute", "use", "operate", "perform", "utilize"}
    verbs_l2 = {"explain", "understand", "describe", "discuss", "outline", "interpret", "summarize", "classify", "illustrate", "comprehend", "distinguish"}
    verbs_l1 = {"define", "recall", "list", "state", "identify", "recognize", "name", "label"}

    detected_verb = words[0] if words else "study"
    verb_level = 2

    for w in first_few:
        if w in verbs_l6:
            verb_level = 6
            detected_verb = w
            break
        elif w in verbs_l5:
            verb_level = 5
            detected_verb = w
            break
        elif w in verbs_l4:
            verb_level = 4
            detected_verb = w
            break
        elif w in verbs_l3:
            verb_level = 3
            detected_verb = w
            break
        elif w in verbs_l2:
            verb_level = 2
            detected_verb = w
            break
        elif w in verbs_l1:
            verb_level = 1
            detected_verb = w
            break

    final_level = explicit_level if explicit_level is not None else verb_level

    level_names = {
        1: "Level 1 (Remember)",
        2: "Level 2 (Understand)",
        3: "Level 3 (Apply)",
        4: "Level 4 (Analyze)",
        5: "Level 5 (Evaluate)",
        6: "Level 6 (Create)"
    }

    return final_level, detected_verb, level_names.get(final_level, f"Level {final_level}")


def extract_topic_summary(co_statement):
    """Extracts a concise, professional summary of the CO's primary pedagogical focus."""
    stmt = (co_statement or "").strip()
    cleaned = re.sub(
        r"^(?:explain|understand|implement|apply|demonstrate|analyze|design|develop|evaluate|to)\s+(?:the\s+)?",
        "", stmt, flags=re.IGNORECASE
    )
    cleaned = cleaned.rstrip(".")
    if len(cleaned) > 85:
        cleaned = cleaned[:82] + "..."
    return cleaned[0].upper() + cleaned[1:] if cleaned else "Core Technical Outcome"


def classify_target_outcome(target_code, target_title, target_desc):
    """
    Classifies a PO or PSO into an outcome category.
    Strictly respects standard PO numbering first to avoid keyword cross-contamination.
    """
    target_id = (target_code or "").upper().replace(" ", "")
    num_match = re.search(r"\d+", target_id)
    target_num = int(num_match.group(0)) if num_match else 0
    full_text = f"{target_code} {target_title} {target_desc}".lower()

    if "PSO" in target_id:
        return "PSO", target_num

    # Number-based classification has absolute first priority for standard POs (1 to 12)
    if target_num == 1:
        return "PO1_KNOWLEDGE", 1
    elif target_num == 2:
        return "PO2_ANALYSIS", 2
    elif target_num == 3:
        return "PO3_DESIGN", 3
    elif target_num == 4:
        return "PO4_INVESTIGATION", 4
    elif target_num == 5:
        return "PO5_TOOLS", 5
    elif target_num == 6:
        return "PO6_SOCIETY", 6
    elif target_num == 7:
        return "PO7_ETHICS", 7
    elif target_num == 8:
        return "PO8_TEAMWORK", 8
    elif target_num == 9:
        return "PO9_COMMUNICATION", 9
    elif target_num == 10:
        return "PO10_MANAGEMENT", 10
    elif target_num in [11, 12]:
        return "PO11_LIFELONG", target_num

    # Fallback only when code lacks an explicit number
    if "knowledge" in full_text and "fundamentals" in full_text:
        return "PO1_KNOWLEDGE", 1
    elif "problem" in full_text and "analysis" in full_text:
        return "PO2_ANALYSIS", 2
    elif "design" in full_text and ("solutions" in full_text or "develop" in full_text):
        return "PO3_DESIGN", 3
    elif "investigation" in full_text or "experiments" in full_text:
        return "PO4_INVESTIGATION", 4
    elif "tool" in full_text and ("usage" in full_text or "modern" in full_text):
        return "PO5_TOOLS", 5
    elif "society" in full_text or "world" in full_text:
        return "PO6_SOCIETY", 6
    elif "ethics" in full_text or "ethical" in full_text:
        return "PO7_ETHICS", 7
    elif "team" in full_text or "teamwork" in full_text:
        return "PO8_TEAMWORK", 8
    elif "communication" in full_text or "communicate" in full_text:
        return "PO9_COMMUNICATION", 9
    elif "management" in full_text or "finance" in full_text:
        return "PO10_MANAGEMENT", 10
    elif "lifelong" in full_text or "life-long" in full_text or "independent learning" in full_text:
        return "PO11_LIFELONG", 11

    return "PO_GENERIC", target_num


def check_academic_relevance(clean_co, bloom_level, action_verb, target_category, target_num, target_title, target_desc, co_topic):
    """
    STAGE A: Strict Academic Relevance Gate.
    Determines whether a defensible relationship exists between the CO and the PO/PSO.
    Returns: (is_relevant, evidence_type, rationale, competency_link)
      - is_relevant: bool
      - evidence_type: 'DIRECT' | 'SUBSTANTIAL' | 'INDIRECT' | 'NONE'
      - rationale: string explanation
      - competency_link: short summary of specific competency
    """
    co_tokens = set(clean_co.split())
    co_sub_tokens = set(extract_substantive_tokens(clean_co))

    # ----------------------------------------------------
    # 1. PO1: Engineering Knowledge (WK1 to WK4)
    # ----------------------------------------------------
    if target_category == "PO1_KNOWLEDGE":
        non_eng_cues = {"orientation", "physical fitness", "recreational", "hostel", "counseling"}
        if co_tokens & non_eng_cues:
            return False, "NONE", f"The CO focuses on '{co_topic}', which lacks core mathematical, scientific, or engineering foundations required by PO1.", "Non-technical activity"
        if bloom_level >= 4:
            return True, "DIRECT", f"The CO imparts core engineering principles and applied computational methods.", "Core engineering principles (WK1-WK4)"
        elif bloom_level == 3:
            return True, "SUBSTANTIAL", f"The CO applies fundamental principles of computing and engineering.", "Applied engineering fundamentals"
        else:
            return True, "INDIRECT", f"The CO develops foundational conceptual understanding of core engineering/computing principles.", "Foundational engineering knowledge"

    # ----------------------------------------------------
    # 2. PO2: Problem Analysis (WK1 to WK4)
    # ----------------------------------------------------
    elif target_category == "PO2_ANALYSIS":
        analysis_terms = {
            "analyze", "analyse", "analysis", "complexity", "efficiency",
            "benchmark", "benchmarking", "formulate", "formulation",
            "diagnose", "diagnosis", "evaluate", "evaluating", "optimization",
            "optimizing", "tradeoff", "tradeoffs", "differentiate"
        }
        matched_analysis = co_sub_tokens & analysis_terms

        if bloom_level >= 4:
            return True, "DIRECT", f"High cognitive demand (Bloom L{bloom_level}) directly exercises analytical formulation, problem decomposition, and efficiency analysis.", f"Problem analysis and decomposition via '{action_verb}'"
        elif matched_analysis:
            if bloom_level == 3:
                return True, "DIRECT", f"CO explicitly addresses analytical requirements ({', '.join(matched_analysis)}) to evaluate computational efficiency and problem formulations.", f"Analytical efficiency ({', '.join(matched_analysis)})"
            else:
                # Conceptual complexity (e.g., DSA CO1: time and space complexity at Bloom L2)
                return True, "INDIRECT", f"CO conceptually introduces analytical complexity metrics ({', '.join(matched_analysis)}) supporting problem analysis.", "Conceptual complexity foundations"
        elif bloom_level == 3 and ("solve" in co_tokens or "computational" in co_tokens):
            return True, "SUBSTANTIAL", f"CO applies problem-solving techniques to computational problems.", "Computational problem solving"
        else:
            return False, "NONE", f"The CO focuses on '{co_topic}' (Bloom L{bloom_level} '{action_verb}') without analytical problem formulation, complexity investigation, or diagnostic modeling required by PO2.", "Lacks analytical demand"

    # ----------------------------------------------------
    # 3. PO3: Design/Development of Solutions (WK5)
    # ----------------------------------------------------
    elif target_category == "PO3_DESIGN":
        design_terms = {
            "design", "architect", "synthesize", "devise", "formulate",
            "implement", "develop", "construct", "build", "create", "program"
        }
        matched_design = co_sub_tokens & design_terms

        if bloom_level in [5, 6] or (co_sub_tokens & {"design", "architect", "synthesize", "devise"}):
            return True, "DIRECT", f"CO explicitly involves creative synthesis and system/algorithmic solution design (Bloom L{bloom_level}).", "System and algorithmic solution design"
        elif bloom_level >= 3 and matched_design:
            return True, "SUBSTANTIAL", f"CO actively develops/implements concrete algorithmic or structural solutions for computational problems.", "Structural solution development"
        elif bloom_level >= 3 and ("traversal" in co_tokens or "representation" in co_tokens or "apply" in co_tokens):
            return True, "SUBSTANTIAL", f"CO realizes operational techniques and structural representations for computing problems.", "Solution realization"
        else:
            return False, "NONE", f"The CO focuses on '{co_topic}' (Bloom L{bloom_level} '{action_verb}') as conceptual explanation or descriptive study. It does not design or develop engineered algorithms, components, or systems specified in PO3.", "Lacks solution design/development"

    # ----------------------------------------------------
    # 4. PO4: Conduct Investigations of Complex Problems (WK8)
    # ----------------------------------------------------
    elif target_category == "PO4_INVESTIGATION":
        invest_terms = {
            "investigate", "investigation", "benchmark", "benchmarking",
            "experiment", "experiments", "experimental", "profile", "profiling",
            "crossvalidation", "metrics", "hypothesize", "hypothesis",
            "empirical", "empirical testing", "interpret"
        }
        if (co_sub_tokens & invest_terms) or "cross validation" in clean_co or "evaluation metrics" in clean_co:
            return True, "DIRECT", f"CO explicitly conducts research-based investigation, empirical benchmarking, or data interpretation.", "Empirical investigation and benchmarking"
        else:
            return False, "NONE", f"The CO focuses on '{co_topic}' without empirical experimentation, investigative benchmarking, or research-based data interpretation specified in PO4.", "Lacks empirical investigation"

    # ----------------------------------------------------
    # 5. PO5: Modern Tool Usage (WK2 and WK6)
    # ----------------------------------------------------
    elif target_category == "PO5_TOOLS":
        explicit_tools = {
            "tool", "tools", "ide", "library", "libraries", "python", "java",
            "pytorch", "tensorflow", "scikit", "cad", "cam", "cae", "matlab",
            "git", "profiler", "debugger", "simulator", "framework"
        }
        matched_tools = co_sub_tokens & explicit_tools

        if matched_tools:
            return True, "DIRECT", f"CO explicitly applies modern engineering/IT tools and libraries ({', '.join(matched_tools)}).", f"Modern tool application ({', '.join(matched_tools)})"
        elif bloom_level >= 4 and ("searching" in co_tokens or "sorting" in co_tokens or "hashing" in co_tokens):
            return True, "SUBSTANTIAL", f"Practical execution of algorithms and efficiency analysis requires programming profilers and software tools.", "Algorithmic execution and profiling"
        elif bloom_level >= 3 and (co_tokens & {"implement", "develop", "train", "traversal", "execution"}):
            return True, "INDIRECT", f"Practical implementation of '{co_topic}' requires programming environments, compilers, and debugging toolchains.", "Practical toolchain execution"
        else:
            return False, "NONE", f"The CO focuses on conceptual understanding or theoretical knowledge of '{co_topic}' without practical execution using modern engineering tools or software.", "Lacks modern tool application"

    # ----------------------------------------------------
    # 6. PO6: The Engineer and Society / The World
    # ----------------------------------------------------
    elif target_category == "PO6_SOCIETY":
        soc_terms = {
            "society", "societal", "public health", "health", "safety",
            "environmental", "environment", "sustainability", "sustainable",
            "legal", "cultural", "community", "social", "welfare"
        }
        matched_soc = co_sub_tokens & soc_terms
        if matched_soc:
            return True, "DIRECT", f"CO explicitly addresses societal, environmental, or sustainability considerations ({', '.join(matched_soc)}).", f"Societal context ({', '.join(matched_soc)})"
        else:
            return False, "NONE", f"The CO focuses on '{co_topic}' and provides no curricular or assessment evidence addressing societal, safety, legal, cultural, or environmental impacts required by PO6.", "No societal context"

    # ----------------------------------------------------
    # 7. PO7: Ethics (WK9)
    # ----------------------------------------------------
    elif target_category == "PO7_ETHICS":
        eth_terms = {
            "ethics", "ethical", "integrity", "privacy", "fairness", "bias",
            "human values", "diversity", "inclusion", "copyright", "ipr",
            "intellectual property", "plagiarism", "confidentiality", "laws"
        }
        matched_eth = co_sub_tokens & eth_terms
        if matched_eth or "data privacy" in clean_co or "legal constraints" in clean_co:
            return True, "DIRECT", f"CO explicitly integrates professional ethics, fairness, privacy, or legal compliance.", "Professional ethics and regulatory compliance"
        else:
            return False, "NONE", f"The CO focuses on technical concepts of '{co_topic}' and provides no curricular evidence addressing professional ethics, data privacy, fairness, or legal compliance required by PO7.", "No ethics context"

    # ----------------------------------------------------
    # 8. PO8: Individual and Collaborative Teamwork
    # ----------------------------------------------------
    elif target_category == "PO8_TEAMWORK":
        team_terms = {
            "team", "teams", "teamwork", "collaborative", "collaboration",
            "group", "multidisciplinary", "peer review", "leadership"
        }
        matched_team = co_sub_tokens & team_terms
        if matched_team:
            return True, "DIRECT", f"CO explicitly requires collaborative teamwork and multidisciplinary group performance.", "Collaborative teamwork"
        else:
            return False, "NONE", f"The CO focuses on individual technical competencies of '{co_topic}' and does not assess collaborative teamwork or multidisciplinary team activities required by PO8.", "No teamwork context"

    # ----------------------------------------------------
    # 9. PO9: Communication
    # ----------------------------------------------------
    elif target_category == "PO9_COMMUNICATION":
        comm_terms = {
            "communication", "communicate", "report", "reports", "documentation",
            "documenting", "presentation", "presentations", "technical writing",
            "speech", "specification", "specifications"
        }
        matched_comm = co_sub_tokens & comm_terms
        if matched_comm or "technical report" in clean_co or "design documentation" in clean_co:
            return True, "DIRECT", f"CO explicitly assesses technical communication, report writing, or formal presentation skills.", "Professional technical communication"
        else:
            return False, "NONE", f"The CO focuses on technical knowledge of '{co_topic}' and does not assess professional engineering documentation, reports, or oral presentations required by PO9. (Cognitive explanation in exams does not assess professional communication).", "No communication artifact/presentation"

    # ----------------------------------------------------
    # 10. PO10: Project Management and Finance
    # ----------------------------------------------------
    elif target_category == "PO10_MANAGEMENT":
        mgmt_terms = {
            "management", "finance", "financial", "economic", "economics",
            "budget", "budgeting", "costing", "lifecycle", "scheduling",
            "resource allocation", "project planning", "risk management", "estimation"
        }
        # Avoid false positives for algorithmic 'cost' (e.g., minimum cost spanning tree, cost function)
        algorithmic_cost = ("minimum cost" in clean_co or "cost function" in clean_co) and not (co_sub_tokens & {"budget", "finance", "project", "economic"})
        matched_mgmt = (co_sub_tokens & mgmt_terms)
        if matched_mgmt and not algorithmic_cost:
            return True, "DIRECT", f"CO explicitly covers engineering management, economic evaluation, or project budgeting.", "Engineering management and finance"
        else:
            return False, "NONE", f"The CO focuses on technical computational concepts of '{co_topic}' and does not assess engineering management principles, budgeting, or project economics required by PO10.", "No project management/finance context"

    # ----------------------------------------------------
    # 11. PO11: Life-Long Learning (WK8)
    # ----------------------------------------------------
    elif target_category == "PO11_LIFELONG":
        if (co_sub_tokens & {"lifelong", "adaptability", "emerging"}) or "life long" in clean_co or "independent learning" in clean_co or "emerging technologies" in clean_co:
            return True, "DIRECT", f"CO explicitly prepares students for independent self-directed learning and emerging technology adaptation.", "Independent life-long learning"
        else:
            return False, "NONE", f"Standard syllabus topics in '{co_topic}' lack the open-ended self-directed exploration or emerging technology adaptation required by PO11 (Life-Long Learning).", "No self-directed/emerging technology component"

    # ----------------------------------------------------
    # 12. PSO: Program Specific Outcomes
    # ----------------------------------------------------
    else:
        target_lower = f"{target_title} {target_desc}".lower()
        is_ai_pso = ("artificial intelligence" in target_lower or "intelligent" in target_lower or "ai" in target_lower)
        is_ds_pso = ("data science" in target_lower or "predictive" in target_lower or "data driven" in target_lower)
        is_mech_pso = ("mechanics" in target_lower or "thermal" in target_lower or "cad" in target_lower or "cam" in target_lower or "manufacturing" in target_lower)

        if is_ai_pso:
            ai_direct = {"ai", "artificial intelligence", "intelligent", "machine learning", "deep learning", "neural", "neural networks", "models", "heuristics"}
            ai_foundational = {"searching", "sorting", "hashing", "graph", "tree", "traversal", "complexity", "algorithm", "algorithms"}
            if (co_sub_tokens & ai_direct) or "ai" in co_tokens or "ethical ai" in clean_co:
                return True, "DIRECT", f"CO directly develops AI models, neural architectures, or intelligent decision algorithms.", "Direct Artificial Intelligence competencies"
            elif "searching" in co_tokens or "sorting" in co_tokens or "hashing" in co_tokens:
                return True, "DIRECT", f"Heuristic searching, sorting, and indexing form the foundational algorithms for intelligent systems and search spaces.", "Foundational search & heuristics for AI"
            elif "non linear" in clean_co or "tree" in clean_co or "graph" in clean_co:
                return True, "DIRECT", f"Tree and graph representations are core structures for state-space search in Artificial Intelligence.", "State-space graph representations for AI"
            elif co_sub_tokens & ai_foundational:
                return True, "SUBSTANTIAL", f"CO covers foundational representations and algorithmic complexity essential to AI state-space systems.", "Foundational algorithms for intelligent systems"
            else:
                return False, "NONE", f"The CO focuses on '{co_topic}', which has no curricular relationship to Artificial Intelligence and Intelligent Systems (PSO1).", "No AI domain alignment"

        elif is_ds_pso:
            ds_direct = {"data science", "dataset", "analytics", "predictive", "statistics", "statistical", "crossvalidation", "metrics", "insight"}
            if (co_sub_tokens & ds_direct) or "cross validation" in clean_co or "evaluation metrics" in clean_co:
                return True, "DIRECT", f"CO directly implements Data Science workflows, predictive analytics, or model evaluation.", "Direct Data Science competencies"
            elif "hashing" in co_tokens or "searching" in co_tokens or "sorting" in co_tokens:
                return True, "DIRECT", f"Hashing, search, and sorting techniques are foundational for high-performance data querying and data indexing in Data Science.", "Data indexing & querying techniques"
            elif "linear" in clean_co or "data structures" in clean_co or "non linear" in clean_co:
                return True, "SUBSTANTIAL", f"CO establishes core linear/non-linear data structures essential for dataset representations.", "Dataset representations and structures"
            elif "ai" in co_tokens or "neural" in co_tokens or "supervised learning" in clean_co:
                return True, "SUBSTANTIAL", f"CO develops predictive models and learning pipelines applied in Data Science.", "Predictive modeling and learning pipelines"
            else:
                return False, "NONE", f"The CO focuses on '{co_topic}', which has no curricular relationship to Data Science and Predictive Analytics (PSO2).", "No Data Science domain alignment"

        elif is_mech_pso:
            mech_terms = {"mechanics", "thermal", "fluid", "thermodynamics", "heat", "stress", "strain", "cad", "cam", "cae", "manufacturing", "machining"}
            if co_sub_tokens & mech_terms:
                return True, "DIRECT", f"CO directly addresses mechanical engineering principles ({', '.join(co_sub_tokens & mech_terms)}).", "Mechanical engineering domain competencies"
            else:
                return False, "NONE", f"The CO focuses on '{co_topic}', which has no curricular relationship to Mechanical Engineering competencies.", "No mechanical domain alignment"

        else:
            pso_content_tokens = set(extract_substantive_tokens(target_desc))
            overlap = co_sub_tokens & pso_content_tokens
            if overlap:
                return True, "SUBSTANTIAL", f"CO aligns with program-specific competencies in {', '.join(overlap)}.", f"Program-specific alignment ({', '.join(overlap)})"
            else:
                return False, "NONE", f"The CO focuses on '{co_topic}', which lacks curricular alignment with the specified Program Specific Outcome.", "No program-specific alignment"


def score_to_mapping(score, is_relevant=True):
    """
    Translates percentage score to OBE mapping scale with strict no-mapping precedence:
      - If is_relevant is False or score == 0.0 -> '-' (0, No Mapping)
      - > 80.0% -> '3' (3, High)
      - 50.0% to 80.0% -> '2' (2, Moderate)
      - < 50.0% -> '1' (1, Low)
    """
    if not is_relevant or score == 0.0:
        return 0, "-", "No Mapping"
    if score > 80.0:
        return 3, "3", "High"
    if score >= 50.0:
        return 2, "2", "Moderate"
    return 1, "1", "Low"


def evaluate_co_target_relationship(co, target_code, target_title, target_desc):
    """
    Conducts a rigorous, explainable two-stage pedagogical evaluation:
    Stage A: Academic Relevance Gate (filters out indefensible / weakly related pairs).
    Stage B: Multi-factor Mapping Strength (only for pairs passing Stage A).
    """
    co_stmt = co.get("statement", "")
    co_bl = co.get("bl", "")
    clean_co = preprocess_text(co_stmt)
    clean_target = preprocess_text(f"{target_title} {target_desc}")

    bloom_level, action_verb, bloom_label = extract_bloom_info(co_stmt, co_bl)
    co_topic = extract_topic_summary(co_stmt)

    target_category, target_num = classify_target_outcome(target_code, target_title, target_desc)

    # 1. STAGE A: ACADEMIC RELEVANCE GATE
    is_relevant, evidence_type, rationale, comp_link = check_academic_relevance(
        clean_co, bloom_level, action_verb, target_category, target_num, target_title, target_desc, co_topic
    )

    if not is_relevant:
        return {
            "value": 0,
            "display": "-",
            "strength": "No Mapping",
            "match_percentage": 0.0,
            "co_topic": co_topic,
            "target_concept": target_title,
            "matching_elements": "No curricular or assessment alignment found",
            "factor_breakdown": {
                "domain_relevance": 0.0,
                "verb_alignment": 0.0,
                "phrase_match": 0.0,
                "semantic_similarity": 0.0
            },
            "is_uncertain": False,
            "review_note": "",
            "reason": f"No Meaningful Relationship (-): {rationale} [Proposed Decision-Support for Teacher Verification]"
        }

    # 2. STAGE B: MAPPING STRENGTH EVALUATION
    # Factor 1: Domain & Curricular Competency Relevance (40% weight)
    if evidence_type == "DIRECT":
        if bloom_level >= 4:
            domain_relevance = 96.0
        elif bloom_level == 3:
            domain_relevance = 88.0
        else:
            domain_relevance = 76.0
    elif evidence_type == "SUBSTANTIAL":
        if bloom_level >= 4:
            domain_relevance = 84.0
        elif bloom_level == 3:
            domain_relevance = 74.0
        else:
            domain_relevance = 60.0
    else:  # INDIRECT
        domain_relevance = 44.0

    # Factor 2: Bloom's Action Verb & Cognitive Demand Alignment (25% weight)
    if target_category == "PO1_KNOWLEDGE":
        verb_score = 95.0 if bloom_level >= 4 else (80.0 if bloom_level == 3 else 54.0)
    elif target_category == "PO2_ANALYSIS":
        verb_score = 96.0 if bloom_level >= 4 else (72.0 if bloom_level == 3 else 46.0)
    elif target_category == "PO3_DESIGN":
        verb_score = 95.0 if bloom_level >= 5 else (88.0 if bloom_level == 4 else (76.0 if bloom_level == 3 else 42.0))
    elif target_category == "PO4_INVESTIGATION":
        verb_score = 94.0 if bloom_level >= 4 else 75.0
    elif target_category == "PO5_TOOLS":
        verb_score = 88.0 if bloom_level >= 4 else (76.0 if bloom_level == 3 else 46.0)
    elif target_category == "PSO":
        verb_score = 95.0 if bloom_level >= 4 else (78.0 if bloom_level == 3 else 58.0)
    else:
        verb_score = 88.0 if bloom_level >= 4 else 70.0

    # Factor 3: Substantive Key Phrase Match (15% weight)
    sub_co_words = extract_substantive_tokens(clean_co)
    sub_target_words = extract_substantive_tokens(clean_target)
    sub_co_str = " ".join(sub_co_words)
    sub_target_str = " ".join(sub_target_words)

    if sub_co_str and sub_target_str:
        tok_set = fuzz.token_set_ratio(sub_co_str, sub_target_str)
        part_rat = fuzz.partial_ratio(sub_co_str, sub_target_str)
        base_phrase = 0.6 * tok_set + 0.4 * part_rat
        if evidence_type == "DIRECT":
            phrase_score = min(100.0, max(75.0, base_phrase * 1.3 + 20.0))
        elif evidence_type == "SUBSTANTIAL":
            phrase_score = min(85.0, max(55.0, base_phrase * 1.0 + 15.0))
        else:
            phrase_score = min(50.0, max(30.0, base_phrase * 0.7 + 10.0))
    else:
        phrase_score = 40.0

    # Factor 4: TF-IDF Semantic Cosine Similarity (20% weight)
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        tfidf_mat = vec.fit_transform([clean_co, clean_target])
        cos_sim = cosine_similarity(tfidf_mat[0:1], tfidf_mat[1:2])[0][0]
        if evidence_type == "DIRECT":
            semantic_score = min(100.0, max(70.0, (cos_sim / 0.25) * 80.0 + 20.0))
        elif evidence_type == "SUBSTANTIAL":
            semantic_score = min(80.0, max(50.0, (cos_sim / 0.25) * 60.0 + 15.0))
        else:
            semantic_score = min(48.0, max(25.0, cos_sim * 100.0))
    except Exception:
        semantic_score = phrase_score

    # Composite Match Percentage (0.0% to 100.0%)
    composite_raw = (
        0.40 * domain_relevance +
        0.25 * verb_score +
        0.15 * phrase_score +
        0.20 * semantic_score
    )
    match_percentage = round(min(100.0, max(1.0, composite_raw)), 1)

    mapping_value, display_val, strength = score_to_mapping(match_percentage, is_relevant=True)

    # Uncertainty / Teacher Review Flag
    is_uncertain = False
    review_note = ""
    if 47.0 <= match_percentage <= 52.0:
        is_uncertain = True
        review_note = f"Borderline score ({match_percentage}%): Near Low (1) / Moderate (2) threshold boundary. Recommended for Teacher Review."
    elif 77.0 <= match_percentage <= 82.0:
        is_uncertain = True
        review_note = f"Borderline score ({match_percentage}%): Near Moderate (2) / High (3) threshold boundary. Recommended for Teacher Review."
    elif evidence_type == "INDIRECT":
        is_uncertain = True
        review_note = f"Indirect relationship ({match_percentage}%): Course outcome provides foundational knowledge but does not directly assess target outcome. Recommended for Teacher Review."

    rule_desc = f"{match_percentage}% > 80.0% -> High (3)" if mapping_value == 3 else (
        f"{match_percentage}% in 50.0%–80.0% -> Moderate (2)" if mapping_value == 2 else
        f"{match_percentage}% < 50.0% -> Low (1)"
    )

    reason = (
        f"Match Score: {match_percentage}% | Mapping: {mapping_value} ({strength}). "
        f"Evidence: {evidence_type.title()} ({comp_link}). "
        f"CO Focus: '{co_topic}'. Target: '{target_title}'. "
        f"Bloom Alignment: {action_verb.title()} ({bloom_label}). "
        f"Threshold Rule: {rule_desc}. [Proposed Decision-Support for Teacher Verification]"
    )
    if review_note:
        reason += f" [Review Flag: {review_note}]"

    return {
        "value": mapping_value,
        "display": display_val,
        "strength": strength,
        "match_percentage": match_percentage,
        "co_topic": co_topic,
        "target_concept": target_title,
        "matching_elements": f"{evidence_type.title()} Alignment: {comp_link}",
        "factor_breakdown": {
            "domain_relevance": round(domain_relevance, 1),
            "verb_alignment": round(verb_score, 1),
            "phrase_match": round(phrase_score, 1),
            "semantic_similarity": round(semantic_score, 1)
        },
        "is_uncertain": is_uncertain,
        "review_note": review_note,
        "reason": reason
    }


def generate_course_suggestions(cos, po_statements, pso_statements):
    """
    Generates explainable, calibrated CO-PO and CO-PSO mappings for a course
    against the department's PO and PSO statements using two-stage academic evaluation.
    """
    suggestions = {}

    for co in cos:
        co_num = co.get("num", "CO1")
        suggestions[co_num] = {}

        # POs
        for po in po_statements:
            po_code = po.get("code", "")
            num_match = re.search(r"\d+", po_code)
            po_num = int(num_match.group(0)) if num_match else 1
            col_key = f"PO {po_num}"
            suggestions[co_num][col_key] = evaluate_co_target_relationship(
                co, po_code, po.get("title", po_code), po.get("desc", "")
            )

        # PSOs
        for pso in pso_statements:
            pso_code = pso.get("code", "")
            num_match = re.search(r"\d+", pso_code)
            pso_num = int(num_match.group(0)) if num_match else 1
            col_key = f"PSO {pso_num}"
            suggestions[co_num][col_key] = evaluate_co_target_relationship(
                co, pso_code, pso_code, pso.get("desc", "")
            )

    return suggestions
