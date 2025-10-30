import re

def detect_intent(text):
    """Detect user intent from message"""
    text = text.lower()
    
    # Check more specific intents FIRST (avoid false positives)
    
    # Government schemes (check before general queries)
    if re.search(r"(scheme|government|sarkari|yojana|loan|subsidy|fund|grant|mudra|pmegp|pmmy)", text):
        return "ask_schemes"
    
    # Ask for ideas
    if re.search(r"(idea|ideas|business|startup|suggest|recommendation|what business|which business)", text):
        return "ask_for_ideas"
    
    # Location/Resources
    if re.search(r"(where|near|nearby|supplier|market|resource|find|shop)", text):
        return "ask_resources"
    
    # Plan generation
    if re.search(r"(plan|how to|step|start|begin|guide|roadmap)", text):
        return "ask_plan"
    
    # Mentor request
    if re.search(r"(mentor|expert|advice|talk|connect)", text):
        return "ask_mentor"
    
    # User info collection - CHECK LOCATION FIRST (more specific pattern)
    if re.search(r"(village|city|town|from|live in|lives in|location)", text):
        return "provide_location"
    
    # Then check for name (less specific - avoid conflicts with "i am from")
    if re.search(r"(my name is|call me|i'm|i am)\s+[a-zA-Z]+(?:\s|$)", text):
        # Only match if followed by a word (not "from", "in", etc.)
        if not re.search(r"(i am|i'm)\s+(from|in|at|interested)", text):
            return "provide_name"
    
    if re.search(r"(interest|like|love|enjoy|passion)", text):
        return "provide_interest"
    
    if re.search(r"(budget|money|rupees|invest|capital)", text):
        return "provide_budget"
    
    # Greeting - ONLY match clear greeting words at start (avoid false positives)
    if re.search(r"^(hello|hi|hey|namaste|start)\b", text):
        return "greeting"
    
    return "general"

def extract_entities(text):
    """Extract entities like name, location, budget, interests"""
    entities = {}
    
    # Skip extraction for button-generated messages (avoid false positives)
    button_phrases = [
        "interested in", "i am interested", "let me tell you", "share my", 
        "i want to", "show me", "find resources", "government schemes",
        "talk to mentor", "create plan", "explore", "continue"
    ]
    
    text_lower = text.lower()
    if any(phrase in text_lower for phrase in button_phrases):
        # This is likely a button click message, skip name/location extraction
        return entities
    
    # Extract name (simple pattern) - must come BEFORE "from" keyword
    # Use negative lookahead to avoid capturing location keywords
    name_match = re.search(r"(my name is|i am|i'm|call me)\s+([a-zA-Z]+)(?:\s+from|\s+in|\s+at|$)", text, re.IGNORECASE)
    if name_match:
        potential_name = name_match.group(2).strip()
        # Filter out common words that aren't names and location names
        excluded_words = ['interested', 'from', 'at', 'in', 'the', 'nashik', 'mumbai', 'pune', 'delhi', 'bangalore']
        if potential_name.lower() not in excluded_words and len(potential_name) > 2:
            entities['name'] = potential_name
    # If no pattern matched, check if it's JUST a name (single capitalized word)
    elif re.match(r"^[A-Z][a-z]+$", text.strip()) and text.strip().lower() not in ['nashik', 'mumbai', 'pune', 'delhi']:
        entities['name'] = text.strip()
    
    # Extract location - with keyword (look for location AFTER the keyword)
    location_match = re.search(r"(?:from|in|at|village|city|town|live in|lives in)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)", text, re.IGNORECASE)
    if location_match:
        potential_location = location_match.group(1).strip()
        # Filter out button phrases, generic words, and common false positives
        excluded_phrases = ['my city', 'my village', 'my location', 'there', 'city', 'village', 'town', 'place', 
                          'the', 'a', 'an', 'this', 'that', 'next', 'first', 'last', 'are the', 'is the']
        if len(potential_location) > 2 and potential_location.lower() not in excluded_phrases:
            # Additional validation: location should be a proper noun (capitalized or all lowercase single word)
            # Reject if it's part of a question like "are the", "what the", etc.
            if not re.search(r"^(are|is|what|where|when|why|how|the)\s", potential_location, re.IGNORECASE):
                entities['location'] = potential_location
    # If no keyword, check if it's just a city/village name (capitalized single/double word)
    elif re.match(r"^[A-Z][a-z]+(\s+[A-Z][a-z]+)?$", text.strip()) and len(text.strip().split()) <= 2:
        # Additional check: Must be standalone, not part of a sentence
        if len(text.split()) <= 2:
            entities['location'] = text.strip()
    
    # Extract budget
    budget_match = re.search(r"(\d+)\s*(thousand|lakh|rupees|rs)", text, re.IGNORECASE)
    if budget_match:
        amount = int(budget_match.group(1))
        unit = budget_match.group(2).lower()
        if 'lakh' in unit:
            amount *= 100000
        elif 'thousand' in unit:
            amount *= 1000
        entities['budget'] = amount
    
    return entities

def categorize_interest(text):
    """Categorize user interests into business categories"""
    text = text.lower()
    categories = []
    
    if re.search(r"(cook|food|snack|pickle|bakery|tiffin|meal)", text):
        categories.append("food")
    
    if re.search(r"(sew|tailor|stitch|cloth|dress|garment|fashion)", text):
        categories.append("tailoring")
    
    if re.search(r"(farm|agriculture|crop|vegetable|organic)", text):
        categories.append("agriculture")
    
    if re.search(r"(milk|dairy|cow|buffalo|ghee|paneer|curd)", text):
        categories.append("dairy")
    
    if re.search(r"(goat|sheep|chicken|poultry|animal)", text):
        categories.append("livestock")
    
    if re.search(r"(beauty|salon|parlour|makeup|mehendi)", text):
        categories.append("beauty")
    
    if re.search(r"(craft|handicraft|art|paint|decoration)", text):
        categories.append("handicraft")
    
    if re.search(r"(tutor|teach|education|class|training)", text):
        categories.append("education")
    
    if re.search(r"(retail|shop|store|sell|kirana)", text):
        categories.append("retail")
    
    return categories if categories else ["general"]
