import re
from fuzzywuzzy import fuzz
from categories import categories

# Minimum similarity threshold for fuzzy matching
FUZZY_MATCH_THRESHOLD = 85

def classify_prompt(prompt):
    prompt_lower = prompt.lower()
    
    # Step 1: Check if the prompt matches any example exactly
    for category, data in categories.items():
        for example in data.get("examples", []):
            if example.lower() == prompt_lower:
                return category

    # Step 2: Check for fuzzy matches in examples (>=85% similarity)
    for category, data in categories.items():
        for example in data.get("examples", []):
            similarity = fuzz.ratio(example.lower(), prompt_lower)
            if similarity >= FUZZY_MATCH_THRESHOLD:
                return category

    # Step 3: Use keywords to match the prompt with categories
    keyword_matches = {}
    
    for category, data in categories.items():
        for keyword in data.get("keywords", []):
            keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(keyword_pattern, prompt_lower):
                if category in keyword_matches:
                    keyword_matches[category] += 1
                else:
                    keyword_matches[category] = 1

    # If a category has the most keyword matches, return it
    if len(keyword_matches) == 1:
        return list(keyword_matches.keys())[0]
    
    elif len(keyword_matches) > 1:
        # Step 4: Resolve conflicts by checking similarity in examples
        max_keyword_category = max(keyword_matches, key=keyword_matches.get)
        possible_categories = [cat for cat, count in keyword_matches.items() if count == keyword_matches[max_keyword_category]]

        if len(possible_categories) == 1:
            return possible_categories[0]

        # Step 5: If there are multiple categories, use example similarity to resolve
        best_category = None
        highest_similarity = 0
        
        for category in possible_categories:
            for example in categories[category].get("examples", []):
                similarity = fuzz.ratio(example.lower(), prompt_lower)
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_category = category
        
        if best_category:
            return best_category
    
    # Default to "Other" if no strong match is found
    return "Other"
