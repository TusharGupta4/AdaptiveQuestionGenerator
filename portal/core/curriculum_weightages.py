"""
Official Board Question Paper Patterns and Subject-Wise Chapter Weightages
Covers:
  - CBSE: Classes 9, 10, 11, 12
  - ICSE / ISC: Classes 9, 10, 11, 12
  - JEE (Main & Advanced): Competitive Track

Every entry defines:
  1. Paper Pattern (Total Marks, Duration, Sections, Question Types, Marks per Question)
  2. Cognitive Difficulty Target (Easy %, Medium %, Hard %)
  3. Chapter/Unit Weightages (Percentage and Marks Range)
"""

CURRICULUM_REGISTRY = {
    # =========================================================================
    # 1. CBSE BOARD - SECONDARY (CLASSES 9 & 10)
    # =========================================================================
    ("CBSE", "10", "Mathematics"): {
        "title": "CBSE Class 10 Standard Mathematics Board Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "Multiple Choice Questions", "question_count": 20, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 5, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 6, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Long Answer Questions", "question_count": 4, "marks_per_question": 5.0, "question_type": "long_answer"},
            {"section_name": "Section E", "description": "Case Study Based Integrated Units", "question_count": 3, "marks_per_question": 4.0, "question_type": "case_based"}
        ],
        "weightages": {
            "Number Systems": {"weightage_percent": 7.5, "target_marks": 6.0, "chapters": ["Real Numbers"]},
            "Algebra": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["Polynomials", "Pair of Linear Equations in Two Variables", "Quadratic Equations", "Arithmetic Progressions"]},
            "Coordinate Geometry": {"weightage_percent": 7.5, "target_marks": 6.0, "chapters": ["Coordinate Geometry"]},
            "Geometry": {"weightage_percent": 18.75, "target_marks": 15.0, "chapters": ["Triangles", "Circles"]},
            "Trigonometry": {"weightage_percent": 15.0, "target_marks": 12.0, "chapters": ["Introduction to Trigonometry", "Some Applications of Trigonometry"]},
            "Mensuration": {"weightage_percent": 12.5, "target_marks": 10.0, "chapters": ["Areas Related to Circles", "Surface Areas and Volumes"]},
            "Statistics and Probability": {"weightage_percent": 13.75, "target_marks": 11.0, "chapters": ["Statistics", "Probability"]}
        }
    },

    ("CBSE", "10", "Science"): {
        "title": "CBSE Class 10 Science Board Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "MCQs & Assertion-Reason", "question_count": 20, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 6, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 7, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Long Answer Questions", "question_count": 3, "marks_per_question": 5.0, "question_type": "long_answer"},
            {"section_name": "Section E", "description": "Case-Based Data Interpretation", "question_count": 3, "marks_per_question": 4.0, "question_type": "case_based"}
        ],
        "weightages": {
            "Chemical Substances - Nature and Behaviour": {"weightage_percent": 31.25, "target_marks": 25.0, "chapters": ["Chemical Reactions and Equations", "Acids, Bases and Salts", "Metals and Non-metals", "Carbon and its Compounds"]},
            "World of Living": {"weightage_percent": 31.25, "target_marks": 25.0, "chapters": ["Life Processes", "Control and Coordination", "How do Organisms Reproduce?", "Heredity and Evolution"]},
            "Natural Phenomena": {"weightage_percent": 15.0, "target_marks": 12.0, "chapters": ["Light - Reflection and Refraction", "The Human Eye and the Colourful World"]},
            "Effects of Current": {"weightage_percent": 16.25, "target_marks": 13.0, "chapters": ["Electricity", "Magnetic Effects of Electric Current"]},
            "Natural Resources": {"weightage_percent": 6.25, "target_marks": 5.0, "chapters": ["Our Environment"]}
        }
    },

    ("CBSE", "10", "Social Science"): {
        "title": "CBSE Class 10 Social Science Board Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "Objective Type MCQs", "question_count": 20, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 4, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 5, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Long Answer Questions", "question_count": 4, "marks_per_question": 5.0, "question_type": "long_answer"},
            {"section_name": "Section E", "description": "Case-Based Source Analysis", "question_count": 3, "marks_per_question": 4.0, "question_type": "case_based"}
        ],
        "weightages": {
            "India and the Contemporary World - II (History)": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["The Rise of Nationalism in Europe", "Nationalism in India", "The Making of a Global World", "The Age of Industrialisation", "Print Culture and the Modern World"]},
            "Contemporary India - II (Geography)": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["Resources and Development", "Forest and Wildlife Resources", "Water Resources", "Agriculture", "Minerals and Energy Resources", "Manufacturing Industries", "Lifelines of National Economy"]},
            "Democratic Politics - II (Political Science)": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["Power Sharing", "Federalism", "Gender, Religion and Caste", "Political Parties", "Outcomes of Democracy"]},
            "Understanding Economic Development (Economics)": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["Development", "Sectors of the Indian Economy", "Money and Credit", "Globalisation and the Indian Economy", "Consumer Rights"]}
        }
    },

    ("CBSE", "9", "Mathematics"): {
        "title": "CBSE Class 9 Mathematics Annual Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "Multiple Choice Questions", "question_count": 20, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 5, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 6, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Long Answer Questions", "question_count": 4, "marks_per_question": 5.0, "question_type": "long_answer"},
            {"section_name": "Section E", "description": "Case Study Integrated Questions", "question_count": 3, "marks_per_question": 4.0, "question_type": "case_based"}
        ],
        "weightages": {
            "Number Systems": {"weightage_percent": 12.5, "target_marks": 10.0, "chapters": ["Number Systems", "Rational Numbers"]},
            "Algebra": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["Polynomials", "Linear Equations in Two Variables"]},
            "Coordinate Geometry": {"weightage_percent": 5.0, "target_marks": 4.0, "chapters": ["Coordinate Geometry"]},
            "Geometry": {"weightage_percent": 33.75, "target_marks": 27.0, "chapters": ["Introduction to Euclid's Geometry", "Lines and Angles", "Triangles", "Quadrilaterals", "Circles"]},
            "Mensuration": {"weightage_percent": 16.25, "target_marks": 13.0, "chapters": ["Heron's Formula", "Surface Areas and Volumes"]},
            "Statistics": {"weightage_percent": 7.5, "target_marks": 6.0, "chapters": ["Statistics"]}
        }
    },

    ("CBSE", "9", "Science"): {
        "title": "CBSE Class 9 Science Annual Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "MCQs & Assertion-Reason", "question_count": 20, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 6, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 7, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Long Answer Questions", "question_count": 3, "marks_per_question": 5.0, "question_type": "long_answer"},
            {"section_name": "Section E", "description": "Case-Based Source Analysis", "question_count": 3, "marks_per_question": 4.0, "question_type": "case_based"}
        ],
        "weightages": {
            "Matter - Its Nature and Behaviour (Chemistry)": {"weightage_percent": 31.25, "target_marks": 25.0, "chapters": ["Matter in Our Surroundings", "Is Matter Around Us Pure", "Atoms and Molecules", "Structure of the Atom"]},
            "Organization in the Living World (Biology)": {"weightage_percent": 27.5, "target_marks": 22.0, "chapters": ["Cell - The Fundamental Unit of Life", "Tissues"]},
            "Motion, Force and Work (Physics)": {"weightage_percent": 33.75, "target_marks": 27.0, "chapters": ["Motion", "Force and Laws of Motion", "Gravitation", "Work and Energy", "Sound"]},
            "Food / Food Production": {"weightage_percent": 7.5, "target_marks": 6.0, "chapters": ["Improvement in Food Resources"]}
        }
    },

    ("CBSE", "9", "Social Science"): {
        "title": "CBSE Class 9 Social Science Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "Objective Type MCQs", "question_count": 20, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 4, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 5, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Long Answer Questions", "question_count": 4, "marks_per_question": 5.0, "question_type": "long_answer"},
            {"section_name": "Section E", "description": "Case-Based Units", "question_count": 3, "marks_per_question": 4.0, "question_type": "case_based"}
        ],
        "weightages": {
            "India and the Contemporary World - I (History)": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["The French Revolution", "Socialism in Europe and the Russian Revolution", "Nazism and the Rise of Hitler", "Forest Society and Colonialism", "Pastoralists in the Modern World"]},
            "Contemporary India - I (Geography)": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["India - Size and Location", "Physical Features of India", "Drainage", "Climate", "Natural Vegetation and Wildlife", "Population"]},
            "Democratic Politics - I (Political Science)": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["What is Democracy? Why Democracy?", "Constitutional Design", "Electoral Politics", "Working of Institutions", "Democratic Rights"]},
            "Economics": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["The Story of Village Palampur", "People as Resource", "Poverty as a Challenge", "Food Security in India"]}
        }
    },

    # =========================================================================
    # 2. CBSE BOARD - SENIOR SECONDARY (CLASSES 11 & 12)
    # =========================================================================
    ("CBSE", "12", "Physics"): {
        "title": "CBSE Class 12 Physics Board Blueprint",
        "total_marks": 70.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.25, "Medium": 0.55, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "MCQs & Assertion-Reason", "question_count": 16, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 5, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 7, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Case Study Based Questions", "question_count": 2, "marks_per_question": 4.0, "question_type": "case_based"},
            {"section_name": "Section E", "description": "Long Answer Questions", "question_count": 3, "marks_per_question": 5.0, "question_type": "long_answer"}
        ],
        "weightages": {
            "Electrostatics & Current Electricity": {"weightage_percent": 22.86, "target_marks": 16.0, "chapters": ["Electric Charges and Fields", "Electrostatic Potential and Capacitance", "Current Electricity"]},
            "Magnetic Effects of Current & Magnetism, EMI and AC": {"weightage_percent": 24.29, "target_marks": 17.0, "chapters": ["Moving Charges and Magnetism", "Magnetism and Matter", "Electromagnetic Induction", "Alternating Current"]},
            "Electromagnetic Waves & Optics": {"weightage_percent": 25.71, "target_marks": 18.0, "chapters": ["Electromagnetic Waves", "Ray Optics and Optical Instruments", "Wave Optics"]},
            "Dual Nature of Radiation, Atoms and Nuclei": {"weightage_percent": 17.14, "target_marks": 12.0, "chapters": ["Dual Nature of Radiation and Matter", "Atoms", "Nuclei"]},
            "Electronic Devices": {"weightage_percent": 10.0, "target_marks": 7.0, "chapters": ["Semiconductor Electronics: Materials, Devices and Simple Circuits"]}
        }
    },

    ("CBSE", "12", "Chemistry"): {
        "title": "CBSE Class 12 Chemistry Board Blueprint",
        "total_marks": 70.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.25, "Medium": 0.55, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "MCQs & Assertion-Reason", "question_count": 16, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 5, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 7, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Case Study Based Questions", "question_count": 2, "marks_per_question": 4.0, "question_type": "case_based"},
            {"section_name": "Section E", "description": "Long Answer Questions", "question_count": 3, "marks_per_question": 5.0, "question_type": "long_answer"}
        ],
        "weightages": {
            "Physical Chemistry": {"weightage_percent": 32.86, "target_marks": 23.0, "chapters": ["Solutions", "Electrochemistry", "Chemical Kinetics"]},
            "Inorganic Chemistry": {"weightage_percent": 20.0, "target_marks": 14.0, "chapters": ["The d- and f-Block Elements", "Coordination Compounds"]},
            "Organic Chemistry": {"weightage_percent": 47.14, "target_marks": 33.0, "chapters": ["Haloalkanes and Haloarenes", "Alcohols, Phenols and Ethers", "Aldehydes, Ketones and Carboxylic Acids", "Amines", "Biomolecules"]}
        }
    },

    ("CBSE", "12", "Mathematics"): {
        "title": "CBSE Class 12 Mathematics Board Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 180,
        "difficulty_target": {"Easy": 0.25, "Medium": 0.55, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A", "description": "Multiple Choice Questions", "question_count": 20, "marks_per_question": 1.0, "question_type": "mcq_single"},
            {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 5, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 6, "marks_per_question": 3.0, "question_type": "short_answer"},
            {"section_name": "Section D", "description": "Long Answer Questions", "question_count": 4, "marks_per_question": 5.0, "question_type": "long_answer"},
            {"section_name": "Section E", "description": "Case Study Based Integrated Questions", "question_count": 3, "marks_per_question": 4.0, "question_type": "case_based"}
        ],
        "weightages": {
            "Relations and Functions": {"weightage_percent": 10.0, "target_marks": 8.0, "chapters": ["Relations and Functions", "Inverse Trigonometric Functions"]},
            "Algebra": {"weightage_percent": 12.5, "target_marks": 10.0, "chapters": ["Matrices", "Determinants"]},
            "Calculus": {"weightage_percent": 43.75, "target_marks": 35.0, "chapters": ["Continuity and Differentiability", "Applications of Derivatives", "Integrals", "Applications of Integrals", "Differential Equations"]},
            "Vectors and Three-Dimensional Geometry": {"weightage_percent": 17.5, "target_marks": 14.0, "chapters": ["Vectors", "Three-Dimensional Geometry"]},
            "Linear Programming": {"weightage_percent": 6.25, "target_marks": 5.0, "chapters": ["Linear Programming"]},
            "Probability": {"weightage_percent": 10.0, "target_marks": 8.0, "chapters": ["Probability"]}
        }
    },

    # =========================================================================
    # 3. ICSE BOARD - SECONDARY (CLASS 10)
    # =========================================================================
    ("ICSE", "10", "Mathematics"): {
        "title": "ICSE Class 10 Mathematics Board Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 150,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Section A (Compulsory)", "description": "MCQs and Short Multi-Part Questions", "question_count": 15, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Section B (Structured)", "description": "Structured Questions (Attempt 4 out of 7)", "question_count": 5, "marks_per_question": 10.0, "question_type": "long_answer"}
        ],
        "weightages": {
            "Commercial Mathematics": {"weightage_percent": 12.5, "target_marks": 10.0, "chapters": ["Goods and Services Tax (GST)", "Banking", "Shares and Dividends"]},
            "Algebra": {"weightage_percent": 27.5, "target_marks": 22.0, "chapters": ["Linear Inequations", "Quadratic Equations in One Variable", "Factorization of Polynomials", "Matrices", "Arithmetic and Geometric Progression"]},
            "Coordinate Geometry": {"weightage_percent": 12.5, "target_marks": 10.0, "chapters": ["Reflection", "Section and Mid-Point Formula", "Equation of a Line"]},
            "Geometry": {"weightage_percent": 20.0, "target_marks": 16.0, "chapters": ["Similarity", "Loci", "Circles", "Tangents and Intersecting Chords"]},
            "Mensuration": {"weightage_percent": 10.0, "target_marks": 8.0, "chapters": ["Cylinder, Cone and Sphere"]},
            "Trigonometry": {"weightage_percent": 10.0, "target_marks": 8.0, "chapters": ["Trigonometric Identities", "Heights and Distances"]},
            "Statistics and Probability": {"weightage_percent": 7.5, "target_marks": 6.0, "chapters": ["Statistics", "Probability"]}
        }
    },

    ("ICSE", "10", "Geography"): {
        "title": "ICSE Class 10 Geography Board Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 120,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Part I (Compulsory)", "description": "Topographical Map, Map of India & Objective Survey", "question_count": 15, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Part II (Structured)", "description": "Structured Regional Geography with diagrams (5 questions)", "question_count": 5, "marks_per_question": 10.0, "question_type": "long_answer"}
        ],
        "weightages": {
            "Topographical Map & Location": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["Topographical Map", "Map of India"]},
            "Climate & Soil Resources": {"weightage_percent": 20.0, "target_marks": 16.0, "chapters": ["Climate of India", "Soils in India"]},
            "Natural Vegetation & Water Resources": {"weightage_percent": 20.0, "target_marks": 16.0, "chapters": ["Natural Vegetation", "Water Resources"]},
            "Mineral and Energy Resources": {"weightage_percent": 15.0, "target_marks": 12.0, "chapters": ["Mineral and Energy Resources"]},
            "Agriculture, Industry & Transport": {"weightage_percent": 20.0, "target_marks": 16.0, "chapters": ["Agriculture in India", "Manufacturing Industries", "Transport", "Waste Management"]}
        }
    },

    ("ICSE", "10", "History & Civics"): {
        "title": "ICSE Class 10 History & Civics Board Blueprint",
        "total_marks": 80.0,
        "duration_minutes": 120,
        "difficulty_target": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
        "sections": [
            {"section_name": "Part I (Compulsory)", "description": "Short Answer Questions (Civics & Modern History)", "question_count": 16, "marks_per_question": 2.0, "question_type": "short_answer"},
            {"section_name": "Part II (Structured)", "description": "Structured Analytical Essay Questions", "question_count": 6, "marks_per_question": 8.0, "question_type": "long_answer"}
        ],
        "weightages": {
            "Civics - The Union Legislature & Executive": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["The Union Parliament", "The President and the Vice-President", "Prime Minister and Council of Ministers"]},
            "Civics - The Judiciary": {"weightage_percent": 12.5, "target_marks": 10.0, "chapters": ["The Supreme Court", "The High Courts and Subordinate Courts"]},
            "History - Indian National Movement": {"weightage_percent": 37.5, "target_marks": 30.0, "chapters": ["First War of Independence, 1857", "Growth of Nationalism", "First Phase of the Indian National Movement", "Second Phase of the Indian National Movement", "Mahatma Gandhi and the National Movement", "Quit India Movement", "Forward Bloc and the INA", "Independence and Partition of India"]},
            "History - The Contemporary World": {"weightage_percent": 25.0, "target_marks": 20.0, "chapters": ["The First World War", "Rise of Dictatorships", "The Second World War", "United Nations", "Major Agencies of the United Nations", "Non-Aligned Movement"]}
        }
    },

    # =========================================================================
    # 4. JEE MAIN - COMPETITIVE TRACK
    # =========================================================================
    ("JEE", "JEE", "Mathematics"): {
        "title": "JEE Main Mathematics Blueprint",
        "total_marks": 100.0,
        "duration_minutes": 60,
        "difficulty_target": {"Easy": 0.20, "Medium": 0.55, "Hard": 0.25},
        "sections": [
            {"section_name": "Section A (MCQ)", "description": "Single Correct MCQs (+4 / -1)", "question_count": 20, "marks_per_question": 4.0, "question_type": "mcq_single"},
            {"section_name": "Section B (Numerical)", "description": "Numerical Value Questions (+4 / -1)", "question_count": 5, "marks_per_question": 4.0, "question_type": "numerical"}
        ],
        "weightages": {
            "Algebra": {"weightage_percent": 32.0, "target_marks": 32.0, "chapters": ["Complex Number", "Quadratic Equations", "Sequences and Series", "Binomial Theorem", "Permutations and Combinations", "Matrices", "Determinants", "Probability", "Statistics"]},
            "Calculus": {"weightage_percent": 35.0, "target_marks": 35.0, "chapters": ["Limit, Continuity, and Differentiability", "Applications of Derivatives", "Indefinite Integration", "Definite Integration", "Differential Equations", "Application of Integrals"]},
            "Coordinate Geometry": {"weightage_percent": 15.0, "target_marks": 15.0, "chapters": ["Straight Lines", "Circles", "Conic Sections: Parabola", "Conic Sections: Ellipse", "Conic Sections: Hyperbola"]},
            "Vectors and 3D": {"weightage_percent": 12.0, "target_marks": 12.0, "chapters": ["Vector Algebra", "Three-Dimensional Geometry"]},
            "Trigonometry": {"weightage_percent": 6.0, "target_marks": 6.0, "chapters": ["Trigonometric Ratios and Identities", "Trigonometric Equations", "Inverse Trigonometric Functions"]}
        }
    }
}

