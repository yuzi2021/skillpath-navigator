"""
Constants for SkillPath Navigator API.

Role keywords and mapping system for matching job titles to role types.

DESIGN PHILOSOPHY:
Users think in terms of specific roles ("Backend Developer", "Frontend Developer"),
but entry-level job titles are often generic ("Junior Coder", "Software Engineer").

This two-tier system:
1. Accepts user's mental model (role names they know)
2. Maps to keywords that actually appear in job titles
3. Ensures effective search results despite title ambiguity

Dataset Context:
- 464 entry-level software engineering jobs (LinkedIn, January 2024)
- Most common titles: "Junior Coder" (147), "Software Engineering Graduate" (31)
- Explicit role titles (backend/frontend) are rare in entry-level positions
"""


# ============================================================================
# TIER 1: User-Facing Role Categories
# ============================================================================
# What users will search for - maps to keyword groups below
# The 8 USER_ROLE_CATEGORIES are based on:
# 1. Industry Standards - Consistent across LinkedIn, Indeed, Stack Overflow
# 2. Bootcamp Training - Aligns with how bootcamp programs are structured
# 3. User Search Behavior - Google Trends validates active searches
# 4. Professional Taxonomy - Stack Overflow 2023 survey developer roles
# 5. Dataset Coverage - 5/8 categories strongly represented in data

USER_ROLE_CATEGORIES = [
    'backend',
    'frontend', 
    'fullstack',
    'data',
    'devops',
    'qa',
    'mobile',
    'software',  # Generic software engineering
]


# ============================================================================
# TIER 2: Keyword Mapping (What's Actually in Job Titles)
# ============================================================================
# Keywords are organized by what they match in the dataset

ROLE_KEYWORDS = {
    # BACKEND (inferred from context, not explicit in titles)
    # Matches: Java developers, API engineers, server-side roles
    # Dataset coverage: ~5-10 jobs with "Java", minimal "backend" in titles
    'backend': [
        'backend', 'back-end', 'back end',
        'server', 'api', 
        'java',  # Java developers are typically backend
    ],
    
    # FRONTEND (minimal in dataset)
    # Matches: UI/UX roles, web developers
    # Dataset coverage: < 5 jobs
    'frontend': [
        'frontend', 'front-end', 'front end',
        'ui', 'ux', 'web', 'client-side',
    ],
    
    # FULL STACK (explicit in dataset)
    # Matches: Full stack developers
    # Dataset coverage: 3 jobs explicitly, more implied
    'fullstack': [
        'full stack', 'full-stack', 'fullstack',
        'full stack developer',
    ],
    
    # DATA (strong presence in dataset)
    # Matches: Data engineers, analysts, scientists
    # Dataset coverage: 50+ jobs (10.8% of dataset)
    'data': [
        'data engineer', 'data analyst', 'data scientist',
        'analyst', 'analytics', 'data', 
        'database', 'dba',  # Database administrators
        'business intelligence', 'bi',
    ],
    
    # DEVOPS/INFRASTRUCTURE (moderate presence)
    # Matches: DevOps, SRE, infrastructure engineers
    # Dataset coverage: 15-20 jobs (3.2-4.3%)
    'devops': [
        'devops', 'dev ops', 
        'infrastructure', 'platform',
        'sre', 'site reliability',
        'systems', 'system administrator',
        'cloud engineer', 'aws', 'azure',
    ],
    
    # QA/TESTING (present in dataset)
    # Matches: Test engineers, QA, SDET
    # Dataset coverage: 7-10 jobs (1.5-2.2%)
    'qa': [
        'qa', 'quality assurance', 'quality',
        'test', 'testing', 'tester',
        'sdet', 'automation engineer',
        'test engineer',
    ],
    
    # MOBILE (not in dataset, but included for completeness)
    # Matches: iOS, Android, mobile developers
    # Dataset coverage: 0 jobs
    'mobile': [
        'mobile', 'ios', 'android',
        'react native', 'flutter', 'swift', 'kotlin',
        'mobile developer', 'mobile engineer',
    ],
    
    # SOFTWARE ENGINEERING (most generic - catches majority)
    # Matches: Generic software roles, coders, programmers
    # Dataset coverage: 180+ jobs (38.8%)
    'software': [
        'software engineer', 'software developer', 'software',
        'coder', 'coding', 'programmer', 'programming',
        'engineer', 'developer', 'development',
        'graduate', 'intern', 'junior',
    ],
}


# ============================================================================
# TIER 3: User Query Normalization
# ============================================================================
# Maps common user queries to role categories
# Handles variations in how users phrase their search

ROLE_ALIASES = {
    # Backend variations
    'backend developer': 'backend',
    'backend engineer': 'backend',
    'back-end developer': 'backend',
    'back end developer': 'backend',
    'server developer': 'backend',
    'api developer': 'backend',
    'java developer': 'backend',  # Common backend language
    
    # Frontend variations
    'frontend developer': 'frontend',
    'frontend engineer': 'frontend',
    'front-end developer': 'frontend',
    'front end developer': 'frontend',
    'ui developer': 'frontend',
    'web developer': 'frontend',
    
    # Full Stack variations
    'full stack developer': 'fullstack',
    'full-stack developer': 'fullstack',
    'fullstack developer': 'fullstack',
    
    # Data variations
    'data engineer': 'data',
    'data analyst': 'data',
    'data scientist': 'data',
    'business analyst': 'data',
    'database administrator': 'data',
    'dba': 'data',
    
    # DevOps variations
    'devops engineer': 'devops',
    'infrastructure engineer': 'devops',
    'platform engineer': 'devops',
    'site reliability engineer': 'devops',
    'sre': 'devops',
    'cloud engineer': 'devops',
    'systems administrator': 'devops',
    
    # QA variations
    'qa engineer': 'qa',
    'test engineer': 'qa',
    'quality assurance': 'qa',
    'sdet': 'qa',
    'automation engineer': 'qa',
    
    # Mobile variations
    'mobile developer': 'mobile',
    'ios developer': 'mobile',
    'android developer': 'mobile',
    
    # Software Engineering variations
    'software engineer': 'software',
    'software developer': 'software',
    'programmer': 'software',
    'coder': 'software',
}


# ============================================================================
# UTILITY: Dataset Statistics
# ============================================================================
# For documentation and reporting purposes

DATASET_ROLE_COVERAGE = {
    'data': 50,          # ~10.8% of jobs
    'software': 180,     # ~38.8% of jobs
    'devops': 15,        # ~3.2% of jobs
    'fullstack': 3,      # ~0.6% of jobs
    'qa': 7,             # ~1.5% of jobs
    'backend': 5,        # ~1.1% of jobs (inferred)
    'frontend': 2,       # ~0.4% of jobs
    'mobile': 0,         # 0% of jobs
}


# ============================================================================
# HELPER FUNCTION: Normalize User Input
# ============================================================================

def normalize_role_query(user_query):
    """
    Normalize user's role query to a standard role category.
    
    Args:
        user_query (str): User's search term (e.g., "Backend Developer")
        
    Returns:
        str: Normalized role category (e.g., "backend")
        
    Example:
        >>> normalize_role_query("Full Stack Developer")
        'fullstack'
        >>> normalize_role_query("backend")
        'backend'
    """
    if not user_query:
        return None
    
    # Convert to lowercase for matching
    query_lower = user_query.lower().strip()
    
    # Check if it's already a valid category
    if query_lower in USER_ROLE_CATEGORIES:
        return query_lower
    
    # Check if it's in our aliases
    if query_lower in ROLE_ALIASES:
        return ROLE_ALIASES[query_lower]
    
    # Check for partial matches (e.g., "backend" in "backend dev")
    for category in USER_ROLE_CATEGORIES:
        if category in query_lower:
            return category
    
    # No match found
    return None


# ============================================================================
# HELPER FUNCTION: Get Keywords for Role
# ============================================================================

def get_keywords_for_role(role_category):
    """
    Get keyword list for a role category.
    
    Args:
        role_category (str): Normalized role category
        
    Returns:
        list: Keywords to search in job titles
        
    Example:
        >>> get_keywords_for_role('backend')
        ['backend', 'back-end', 'back end', 'server', 'api', 'java']
    """
    return ROLE_KEYWORDS.get(role_category, [])


"""
Constants for SkillPath Navigator API.

Skill categorization lists for filtering technical vs soft skills.
"""

# Reliable technical skill categories
TECHNICAL_CATEGORIES = [
    'LANGUAGE',      # Python, JavaScript, Java, etc.
    'FRAMEWORK',     # React, Django, Angular, etc.
    'DATABASE',      # SQL, PostgreSQL, MongoDB, etc.
    'TOOLS',         # Git, Docker, Jenkins, etc.
    'CLOUD_DEVOPS'   # AWS, Azure, Kubernetes, etc.
]

# Known soft skills (manually curated from OTHER category)
SOFT_SKILLS = [
    'adaptability',
    'attention to detail',
    'clean code',
    'clean coding',
    'code review',
    'coding',
    'collaboration',
    'communication',
    'critical thinking',
    'debugging',
    'leadership',
    'mathematics',
    'problem solving',
    'teamwork',
    'time management'
]

# Non-skills to exclude from all results
EXCLUDE_SKILLS = [
    'bachelors degree',
    'bachelors degree in stem',
    'beng',
    'bsc',
    'cashback',
    'competitive pension scheme',
    'competitive salary'
]





