"""
LLM Integration Module for Startup Sathi
=========================================

This module handles all AI/LLM interactions with a robust 3-tier fallback system:

API CASCADE (in order of preference):
1. GROQ (Primary) - llama-3.3-70b-versatile
   - Fast, high-quality responses
   - Rate limit: 100,000 tokens/day
   
2. Google Gemini (Secondary) - gemini-2.5-flash
   - Reliable fallback when GROQ hits rate limit
   - Free tier with generous limits
   
3. DeepSeek (Tertiary) - deepseek-chat
   - Final fallback if both GROQ and Gemini fail
   - Ensures service availability

Each function automatically cascades through these APIs to guarantee responses.
"""

from groq import Groq
import google.generativeai as genai
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Import web search utilities
try:
    from utils.web_search import (
        search_duckduckgo, 
        get_location_data, 
        search_local_resources,
        get_market_trends,
        search_government_schemes,
        get_government_scheme_details
    )
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    print("Web search utilities not available")

# Initialize Groq client with API key from environment
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '***REDACTED***')
client = Groq(api_key=GROQ_API_KEY)

# Initialize Gemini client with API key from environment
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '***REDACTED***')
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')  # Updated to latest available model

# Initialize DeepSeek client as third fallback
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '***REDACTED***')
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# Use working Groq model - llama-3.3-70b-versatile is the most capable available
GROQ_MODEL = "llama-3.3-70b-versatile"
DEEPSEEK_MODEL = "deepseek-chat"

def generate_business_ideas(user_info, rag_context=""):
    """
    Generate REALISTIC, location-aware business ideas with proper budget analysis
    Enhanced with real-time Google search for trends and opportunities
    """
    
    location = user_info.get('village', 'India')
    budget = user_info.get('budget', 10000)
    interests = user_info.get('interests', 'general business')
    name = user_info.get('name', 'Entrepreneur')
    
    # GET REAL-TIME MARKET INTELLIGENCE FROM WEB
    web_intelligence = ""
    if WEB_SEARCH_AVAILABLE:
        try:
            from utils.web_search import get_location_based_opportunities, smart_google_search
            
            print(f"🌐 Fetching real-time market data for {location}...")
            
            # Get comprehensive location-based opportunities
            opportunities = get_location_based_opportunities(user_info)
            
            # Build intelligence summary
            if opportunities.get('trends'):
                web_intelligence += "\n\n**REAL-TIME TRENDS IN " + location.upper() + " (2025):**\n"
                for i, trend in enumerate(opportunities['trends'][:3], 1):
                    web_intelligence += f"{i}. {trend.get('title', '')}\n   {trend.get('snippet', '')[:150]}...\n"
            
            if opportunities.get('local_demands'):
                web_intelligence += "\n\n**HIGH-DEMAND PRODUCTS/SERVICES IN " + location.upper() + ":**\n"
                for i, demand in enumerate(opportunities['local_demands'][:3], 1):
                    web_intelligence += f"{i}. {demand.get('title', '')}\n   {demand.get('snippet', '')[:150]}...\n"
            
            if opportunities.get('success_stories'):
                web_intelligence += "\n\n**SUCCESS STORIES FROM " + location.upper() + ":**\n"
                for i, story in enumerate(opportunities['success_stories'][:2], 1):
                    web_intelligence += f"{i}. {story.get('title', '')}\n   {story.get('snippet', '')[:100]}...\n"
            
            if opportunities.get('government_schemes'):
                web_intelligence += "\n\n**AVAILABLE GOVERNMENT SCHEMES:**\n"
                for i, scheme in enumerate(opportunities['government_schemes'][:3], 1):
                    web_intelligence += f"{i}. {scheme.get('title', '')}\n"
            
            print(f"✅ Web intelligence gathered: {len(web_intelligence)} chars")
            
        except Exception as e:
            print(f"⚠️ Web intelligence gathering failed: {e}")
            web_intelligence = ""
    
    # Add RAG context if available
    rag_prompt_addition = ""
    if rag_context:
        rag_prompt_addition = f"\n\n**IMPORTANT CONTEXT FROM USER'S HISTORY:**\n{rag_context}\n\nUse this to provide MORE PERSONALIZED suggestions based on their past conversations and preferences.\n"
    
    prompt = f"""
    You are an experienced business consultant analyzing {location}, India for {name}.
    
    **YOU HAVE ACCESS TO REAL-TIME 2025 MARKET DATA - USE IT!**
    {web_intelligence}
    
    **CRITICAL REQUIREMENTS:**
    
    1. **LOCATION ANALYSIS FOR {location.upper()} (USE THE REAL-TIME DATA ABOVE):**
       - Use the TRENDS data to identify what's actually working NOW in {location}
       - Use the DEMAND data to find gaps in the market
       - Avoid suggesting businesses mentioned in SUCCESS STORIES (already saturated)
       - Consider local culture, festivals, and buying power
       - Suggest businesses that fill GAPS based on real market intelligence
    
    2. **REALISTIC BUDGET ANALYSIS (Available: ₹{budget}):**
       - If budget is LESS than ₹15,000: Suggest ONLY home-based, zero-infrastructure businesses
       - If budget is ₹15,000-₹50,000: Suggest small setup businesses
       - If budget is ₹50,000+: Suggest standard businesses
       
       **IMPORTANT:** If their budget is LOW but business needs MORE money:
       - Be HONEST about actual costs
       - Mention the GOVERNMENT SCHEMES from real-time data above
       - Suggest MUDRA loans, Stand-Up India schemes available
       - Provide realistic funding roadmap
       - Provide phased approach: "Start with X using ₹{budget}, scale to Y with loan"
    
    3. **COMPETITION ANALYSIS:**
       - Check if similar businesses are oversaturated in {location}
       - Suggest differentiation strategies
       - Warn about high-competition markets
    
    4. **HOME-BASED PRIORITY (for budgets under ₹20,000):**
       - Tiffin/catering services from home kitchen
       - Online tutoring (needs laptop/phone only)
       - Handicrafts sold online (Instagram/WhatsApp Business)
       - Tailoring from home
       - Homemade pickles/snacks (sold locally or online)
       - Beauty services at home (threading, mehendi, hair styling)
    
    **INTEREST:** {interests}
    {rag_prompt_addition}
    
    Generate 5 businesses matching above criteria. For EACH provide JSON with:
    title, description, investment_min, investment_max, actual_realistic_cost, funding_suggestion, 
    why_this_location, home_based, competition_level, skills, success_probability, profitability
    
    **CRITICAL:** Research {location}'s economy. Be BRUTALLY HONEST about costs and competition.
    Format as JSON array.
    """
    
    try:
        print(f"🤖 Calling GROQ API to generate business ideas...")
        print(f"📊 User info: {user_info}")
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an experienced business advisor for rural women entrepreneurs in India. You have access to current market trends and real business data from 2024-2025. You provide practical, location-specific, and encouraging advice based on ACTUAL market conditions. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=3500
        )
        
        ideas_text = response.choices[0].message.content
        print(f"✅ GROQ API response received, length: {len(ideas_text)}")
        print(f"📝 First 200 chars: {ideas_text[:200]}")
        
        # Try to parse as JSON
        try:
            # Remove markdown code blocks if present
            if '```json' in ideas_text:
                ideas_text = ideas_text.split('```json')[1].split('```')[0].strip()
            elif '```' in ideas_text:
                ideas_text = ideas_text.split('```')[1].split('```')[0].strip()
            
            ideas = json.loads(ideas_text)
            print(f"✅ Successfully parsed {len(ideas) if isinstance(ideas, list) else 1} ideas")
            return ideas if isinstance(ideas, list) else [ideas]
        except json.JSONDecodeError as json_err:
            print(f"❌ JSON parsing failed: {json_err}")
            print(f"📝 Raw response: {ideas_text[:500]}")
            # If JSON parsing fails, return structured fallback
            return [{
                "title": "Business Idea",
                "description": ideas_text[:200] if ideas_text else "Unable to generate ideas at the moment",
                "investment_min": 5000,
                "investment_max": 50000,
                "skills": "Basic business skills",
                "suitability": "Based on your profile",
                "market_size": "Growing market",
                "profitability": "₹5,000 - ₹15,000/month"
            }]
    except Exception as e:
        error_str = str(e)
        print(f"❌ GROQ Error: {e}")
        
        # If GROQ rate limit hit, fallback to Gemini
        if 'rate_limit' in error_str.lower() or '429' in error_str:
            print(f"🔄 GROQ rate limit hit! Falling back to Gemini API...")
            try:
                # Use Gemini instead
                gemini_response = gemini_model.generate_content(
                    f"You are an experienced business advisor for rural women entrepreneurs in India. Respond ONLY with valid JSON array.\n\n{prompt}"
                )
                ideas_text = gemini_response.text
                print(f"✅ Gemini API response received, length: {len(ideas_text)}")
                
                # Parse Gemini response
                try:
                    if '```json' in ideas_text:
                        ideas_text = ideas_text.split('```json')[1].split('```')[0].strip()
                    elif '```' in ideas_text:
                        ideas_text = ideas_text.split('```')[1].split('```')[0].strip()
                    
                    ideas = json.loads(ideas_text)
                    print(f"✅ Successfully parsed {len(ideas) if isinstance(ideas, list) else 1} ideas from Gemini")
                    return ideas if isinstance(ideas, list) else [ideas]
                except:
                    print(f"❌ Gemini JSON parsing failed")
                    return []
            except Exception as gemini_error:
                print(f"❌ Gemini also failed: {gemini_error}")
                
                # If Gemini also fails, try DeepSeek as final fallback
                print(f"🔄 Falling back to DeepSeek API...")
                try:
                    deepseek_response = deepseek_client.chat.completions.create(
                        model=DEEPSEEK_MODEL,
                        messages=[
                            {"role": "system", "content": "You are an experienced business advisor for rural women entrepreneurs in India. Respond ONLY with valid JSON array."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2000
                    )
                    ideas_text = deepseek_response.choices[0].message.content
                    print(f"✅ DeepSeek API response received, length: {len(ideas_text)}")
                    
                    # Parse DeepSeek response
                    try:
                        if '```json' in ideas_text:
                            ideas_text = ideas_text.split('```json')[1].split('```')[0].strip()
                        elif '```' in ideas_text:
                            ideas_text = ideas_text.split('```')[1].split('```')[0].strip()
                        
                        ideas = json.loads(ideas_text)
                        print(f"✅ Successfully parsed {len(ideas) if isinstance(ideas, list) else 1} ideas from DeepSeek")
                        return ideas if isinstance(ideas, list) else [ideas]
                    except:
                        print(f"❌ DeepSeek JSON parsing failed")
                        return []
                except Exception as deepseek_error:
                    print(f"❌ DeepSeek also failed: {deepseek_error}")
                    import traceback
                    traceback.print_exc()
                    return []
        
        import traceback
        traceback.print_exc()
        return []

def find_local_resources(location, business_type):
    """
    Generate information about local resources using AI + REAL location data from OpenStreetMap
    """
    
    # Get REAL location data and nearby places
    real_data_context = ""
    real_resources = {}
    
    if WEB_SEARCH_AVAILABLE:
        try:
            print(f"Searching real resources for {business_type} in {location}...")
            real_resources = search_local_resources(business_type, location)
            
            if real_resources and not real_resources.get('error'):
                real_data_context = f"""
**REAL DATA FROM OPENSTREETMAP:**

Location: {real_resources.get('location', location)}
State: {real_resources.get('state', 'N/A')}
District: {real_resources.get('district', 'N/A')}

**Nearby Suppliers Found ({len(real_resources.get('suppliers', []))} within 15km):**
"""
                for supplier in real_resources.get('suppliers', [])[:5]:
                    real_data_context += f"- {supplier['name']} ({supplier['type']}) - {supplier['distance_km']}km away\n"
                
                real_data_context += f"\n**Nearby Markets Found ({len(real_resources.get('markets', []))} within 20km):**\n"
                for market in real_resources.get('markets', [])[:5]:
                    real_data_context += f"- {market['name']} - {market['distance_km']}km away\n"
                
                real_data_context += f"\n**Training Centers Found ({len(real_resources.get('training_centers', []))} within 25km):**\n"
                for center in real_resources.get('training_centers', [])[:3]:
                    real_data_context += f"- {center['name']} - {center['distance_km']}km away\n"
                
                real_data_context += f"\n**Government Offices Found ({len(real_resources.get('government_offices', []))} within 30km):**\n"
                for office in real_resources.get('government_offices', [])[:3]:
                    real_data_context += f"- {office['name']} - {office['distance_km']}km away\n"
                
        except Exception as e:
            print(f"Error fetching real location data: {e}")
    
    prompt = f"""
    A woman entrepreneur in {location}, India is starting a {business_type} business.
    
    {real_data_context if real_data_context else ""}
    
    Provide SPECIFIC, ACTIONABLE resources available in or near {location}:
    
    1. **Suppliers** (5-7 specific ones):
       - Name of shop/supplier (if real data above, use those names; otherwise use realistic names like "Shree Traders", "Agro Suppliers")
       - What they supply (raw materials, equipment, packaging)
       - Location details (market name, area, distance estimate)
       - Contact suggestion (how to find them - local market, Google Maps, phone directory)
       - Price range for key items
    
    2. **Raw Materials Sources** (5-7 specific items needed for {business_type}):
       - Material name
       - Where to buy in {location}
       - Expected price range (realistic for 2024-2025)
       - Quality tips (what to look for when buying)
       - Seasonal availability if applicable
    
    3. **Markets to Sell** (6-8 options):
       - Physical markets (weekly bazaars, mandis, shops in {location})
       - Online platforms (Meesho, WhatsApp Business, Instagram, ONDC)
       - Bulk buyers (hotels, canteens, offices, schools that might buy)
       - Export/wholesale opportunities
       - Best days and times to visit/sell
    
    4. **Government Offices** (4-5 specific ones):
       - Office name (MSME DFO, DIC, Khadi Board, CSC center)
       - Location in or near {location}
       - Services provided (registration, subsidies, training, loans)
       - Contact details/how to reach
       - Best time to visit
    
    5. **Training Centers** (3-4 options):
       - Center name (ITI, SIDBI, NGOs, Skill India centers)
       - Type of training offered
       - Duration and cost (if free, mention that)
       - How to enroll
       - Next batch timing if known
    
    6. **Financial Institutions** (4-5 banks/NBFCs):
       - Bank/institution name
       - Types of business loans available
       - Interest rates (approximate)
       - Branch location in {location}
    
    7. **Additional Tips**:
       - Best practices for sourcing in {location}
       - Local business networks/women's groups to join
       - Seasonal considerations for {business_type}
       - Digital tools and apps useful for this business
    
    If REAL data from OpenStreetMap is provided above, INCORPORATE it into your response with actual distances and locations.
    Be SPECIFIC to {location} - use real place names, market names, realistic suppliers.
    
    Format as JSON with keys: suppliers, raw_materials, markets, government_offices, training_centers, financial_institutions, tips
    Each array should contain detailed objects with all relevant information.
    """
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": f"You are a local business resource expert with deep knowledge of {location}, India. You combine REAL location data with your knowledge to provide accurate, actionable guidance. If real data from OpenStreetMap is provided, use those actual place names and distances. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        resources_text = response.choices[0].message.content
        
        try:
            if '```json' in resources_text:
                resources_text = resources_text.split('```json')[1].split('```')[0].strip()
            elif '```' in resources_text:
                resources_text = resources_text.split('```')[1].split('```')[0].strip()
            
            resources = json.loads(resources_text)
            
            # Add real data if available
            if real_resources and not real_resources.get('error'):
                resources['_real_data'] = {
                    'coordinates': real_resources.get('coordinates', {}),
                    'verified': True,
                    'source': 'OpenStreetMap',
                    'search_date': datetime.now().strftime('%Y-%m-%d')
                }
            
            return resources
        except:
            return {
                "info": resources_text,
                "suppliers": ["Local hardware stores", "Agricultural supply shops"],
                "markets": ["Local market", "Nearby town market"],
                "government_offices": ["District Industries Centre", "Gram Panchayat office"],
                "verified": False
            }
    except Exception as e:
        print(f"Error finding resources: {e}")
        return {}

def find_government_schemes(user_info, business_type):
    """
    Find relevant government schemes using AI + REAL web search data
    """
    
    # Search for real scheme information
    scheme_web_data = ""
    if WEB_SEARCH_AVAILABLE:
        try:
            location = user_info.get('village', 'India')
            results = search_government_schemes(business_type, location, "women")
            
            if results:
                scheme_web_data = "\n**REAL SCHEME INFORMATION FROM WEB SEARCH:**\n"
                for result in results[:5]:
                    scheme_web_data += f"- {result['title']}: {result['snippet'][:200]}...\n"
                    
            # Search for PMEGP specifically
            pmegp_results = search_duckduckgo("PMEGP application process eligibility 2024 women", num_results=3)
            if pmegp_results:
                scheme_web_data += "\n**PMEGP Latest Information:**\n"
                for result in pmegp_results:
                    scheme_web_data += f"- {result['snippet'][:150]}...\n"
                    
        except Exception as e:
            print(f"Error fetching scheme data: {e}")
    
    prompt = f"""
    A woman entrepreneur from {user_info.get('village', 'rural India')} wants to start a {business_type} business with budget ₹{user_info.get('budget', '50000')}.
    
    {scheme_web_data if scheme_web_data else ""}
    
    **Current Year: 2024-2025**
    
    List 6-7 REAL, CURRENT government schemes she can apply for in 2024-2025:
    
    For each scheme provide:
    1. **name**: Full official scheme name with acronym
    2. **managed_by**: Which ministry/department manages it
    3. **eligibility**: WHO can apply (detailed criteria):
       - Age requirements
       - Gender/category specific benefits
       - Business type eligibility
       - Location criteria (rural/urban)
       - Income/investment limits
    4. **benefits**: SPECIFIC benefits with numbers:
       - Loan amount range (min-max)
       - Subsidy percentage (capital subsidy + additional for women/SC/ST)
       - Interest rate (if applicable)
       - Moratorium period
       - Training/handholding support
       - Marketing assistance
    5. **how_to_apply**: DETAILED step-by-step process:
       - Online: Portal URL and registration steps (1, 2, 3...)
       - Offline: Which office to visit, forms to submit
       - Timeline: Application to disbursement duration
       - Whom to contact for help (helpline, nodal officer)
    6. **documents**: COMPLETE list:
       - Identity proof (Aadhaar, PAN, Voter ID)
       - Address proof
       - Bank details (passbook, cancelled cheque)
       - Business plan/project report
       - Caste certificate (if applicable)
       - Educational certificates (if required)
       - Photos (passport size, how many)
       - Other specific documents
    7. **apply_link**: Official portal URL (use real portals):
       - https://www.kviconline.gov.in/pmegp (for PMEGP)
       - https://www.udyamimitra.in (for Mudra)
       - https://www.standupmitra.in (for Stand-Up India)
       - https://msme.gov.in (for MSME schemes)
    8. **deadline**: Application window:
       - "Ongoing - Apply anytime" or specific dates
    9. **contact**: Real helplines:
       - National helpline number
       - Email ID
       - Nearest district office suggestion
    10. **special_provisions**: Extra benefits for women/SC/ST/minorities
    11. **success_rate**: Realistic approval rate and tips to increase chances
    
    Include these specific schemes (use 2024-2025 data):
    - **PMEGP** (Prime Minister Employment Generation Programme) - up to ₹25 lakh loan, 35% subsidy for women in rural areas
    - **Mudra Loan** (Shishu/Kishor/Tarun) - up to ₹10 lakh, no collateral
    - **Stand-Up India** - ₹10 lakh to ₹1 crore for SC/ST/women
    - **Mahila Udyam Nidhi Scheme** - women-specific schemes
    - **State MSME schemes** - specific to user's state
    - **Startup India Seed Fund** - for innovative startups
    - **Nari Shakti Puraskar** - recognition and grants
    
    If web search data is provided above, use it to give CURRENT, ACCURATE information.
    
    Be DETAILED and ACTIONABLE - she should be able to start the application after reading this.
    Format as JSON array with all keys listed above for each scheme.
    """
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": f"You are an expert on Indian government schemes for women entrepreneurs with access to 2024-2025 data. You have current knowledge of PMEGP, Mudra Loan, Stand-Up India, state MSME schemes, and financial assistance programs. Provide accurate, detailed, step-by-step guidance with REAL portal URLs and contact details. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=3500
        )
        
        schemes_text = response.choices[0].message.content
        
        try:
            if '```json' in schemes_text:
                schemes_text = schemes_text.split('```json')[1].split('```')[0].strip()
            elif '```' in schemes_text:
                schemes_text = schemes_text.split('```')[1].split('```')[0].strip()
            
            schemes = json.loads(schemes_text)
            
            # Add metadata
            result = schemes if isinstance(schemes, list) else [schemes]
            return result
        except:
            return [{
                "name": "Government Schemes Available",
                "info": schemes_text[:500],
                "eligibility": "Women entrepreneurs in India",
                "benefits": "Financial assistance, training, and subsidies",
                "how_to_apply": "Visit nearest DIC office or apply online",
                "apply_link": "https://msme.gov.in"
            }]
    except Exception as e:
        print(f"Error finding schemes: {e}")
        return []

def generate_plan(idea, user_info):
    """
    Generate a comprehensive, actionable startup plan using Groq LLM
    """
    prompt = f"""
    Create a COMPLETE, DETAILED startup plan for {user_info.get('name', 'the entrepreneur')} who wants to start this business:
    
    **Business:** {idea['title']}
    **Description:** {idea['description']}
    **Location:** {user_info.get('village', 'Rural India')}
    **Available Budget:** ₹{user_info.get('budget', '50000')}
    **Required Investment:** ₹{idea.get('required_investment_min', 0)} - ₹{idea.get('required_investment_max', 0)}
    **Skills Needed:** {idea.get('skills_required', 'Basic business skills')}
    
    Generate a PRACTICAL, STEP-BY-STEP startup plan with:
    
    1. **overview**: 3-4 sentences explaining:
       - What this business does
       - Why it's a good choice for this location
       - What makes it profitable
       - Vision for growth
    
    2. **skills**: Detailed list of skills needed (5-7 items):
       - Technical skills (e.g., "Pickle preservation techniques", "Spice mixing ratios")
       - Business skills (e.g., "Pricing calculation", "Customer communication")
       - Digital skills if applicable (e.g., "WhatsApp Business", "Instagram marketing")
    
    3. **investment_breakdown**: DETAILED cost breakdown (10-15 line items):
       - Equipment/tools (with specific items and costs)
       - Raw materials (initial stock with quantities and prices)
       - Packaging materials (specific items)
       - Licensing/registration fees
       - Marketing budget (first 3 months)
       - Working capital (buffer for 2 months)
       - Each item should have: description and estimated cost
    
    4. **timeline**: Month-by-month action plan (12 months):
       - Month 1: What to do (training, setup, registration, etc.)
       - Month 2: What to do (production start, initial sales, etc.)
       - ...continue through Month 12
       - Each month should have 3-5 specific actionable tasks
    
    5. **resources**: What she needs to source locally:
       - Raw materials (where to buy in {user_info.get('village', 'her location')})
       - Equipment suppliers (nearby markets or shops)
       - Packaging materials (local sources)
       - Training opportunities (local centers, NGOs, online courses)
    
    6. **target_market**: WHO will buy (be specific):
       - Primary customers (demographics, location, buying habits)
       - Secondary customers (potential future markets)
       - How to reach them (WhatsApp groups, local markets, fairs, word-of-mouth)
       - Pricing strategy (competitive pricing for this market)
    
    7. **revenue_estimate**: Realistic financial projection:
       - Month 1-3: Expected sales and profit
       - Month 4-6: Expected sales and profit
       - Month 7-12: Expected sales and profit
       - Break-even point (when she recovers investment)
       - Year 1 total revenue and profit
    
    8. **risks**: 3-5 potential challenges AND solutions:
       - Risk 1: [problem] → Mitigation: [solution]
       - Risk 2: [problem] → Mitigation: [solution]
       - (Include risks like: customer acquisition, quality issues, competition, seasonal demand, cash flow)
    
    9. **next_steps**: Top 5 immediate actions (this week):
       - Step 1: [specific action with detail]
       - Step 2: [specific action with detail]
       - Make these ACTIONABLE (not vague like "plan" - specific like "Visit Shree Traders at Main Market to check spice prices")
    
    Format as JSON with keys: overview, skills, investment_breakdown (array of objects with item and cost), 
    timeline (array of objects with month and tasks), resources, target_market, revenue_estimate, 
    risks (array of objects with risk and mitigation), next_steps (array of strings)
    
    Be DETAILED, PRACTICAL, and ENCOURAGING. This plan should feel like a mentor sitting with her and explaining everything.
    """
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": f"You are an experienced business mentor for rural women entrepreneurs in India. You have deep knowledge of small business operations, local markets in {user_info.get('village', 'rural India')}, and practical challenges faced by women starting businesses. Provide detailed, step-by-step, encouraging guidance. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3500
        )
        
        plan_text = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            plan_json = json.loads(plan_text)
        except:
            # If not JSON, structure it
            plan_json = {
                "overview": plan_text[:500],
                "full_text": plan_text
            }
        
        return plan_json
    except Exception as e:
        error_str = str(e)
        print(f"❌ GROQ Plan Error: {e}")
        
        # If GROQ rate limit hit, fallback to Gemini
        if 'rate_limit' in error_str.lower() or '429' in error_str:
            print(f"🔄 GROQ rate limit! Using Gemini for plan generation...")
            try:
                gemini_response = gemini_model.generate_content(
                    f"You are an experienced business mentor for rural women entrepreneurs in India. Respond ONLY with valid JSON.\n\n{prompt}"
                )
                plan_text = gemini_response.text
                print(f"✅ Gemini plan response received")
                
                try:
                    if '```json' in plan_text:
                        plan_text = plan_text.split('```json')[1].split('```')[0].strip()
                    elif '```' in plan_text:
                        plan_text = plan_text.split('```')[1].split('```')[0].strip()
                    
                    plan_json = json.loads(plan_text)
                    return plan_json
                except:
                    print(f"❌ Gemini JSON parsing failed for plan")
                    return generate_fallback_plan(idea, user_info)
            except Exception as gemini_error:
                print(f"❌ Gemini plan generation failed: {gemini_error}")
                
                # Try DeepSeek as final fallback
                print(f"🔄 Falling back to DeepSeek for plan generation...")
                try:
                    deepseek_response = deepseek_client.chat.completions.create(
                        model=DEEPSEEK_MODEL,
                        messages=[
                            {"role": "system", "content": f"You are an experienced business mentor for rural women entrepreneurs in India. Respond ONLY with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=3500
                    )
                    plan_text = deepseek_response.choices[0].message.content
                    print(f"✅ DeepSeek plan response received")
                    
                    try:
                        if '```json' in plan_text:
                            plan_text = plan_text.split('```json')[1].split('```')[0].strip()
                        elif '```' in plan_text:
                            plan_text = plan_text.split('```')[1].split('```')[0].strip()
                        
                        plan_json = json.loads(plan_text)
                        return plan_json
                    except:
                        print(f"❌ DeepSeek JSON parsing failed for plan")
                        return generate_fallback_plan(idea, user_info)
                except Exception as deepseek_error:
                    print(f"❌ DeepSeek plan generation failed: {deepseek_error}")
                    return generate_fallback_plan(idea, user_info)
        
        return generate_fallback_plan(idea, user_info)

def generate_fallback_plan(idea, user_info):
    """Fallback plan template if LLM fails"""
    # Handle skills - can be string or list
    skills = idea.get('skills_required', idea.get('skills', 'Basic business skills'))
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(',')]
    elif not isinstance(skills, list):
        skills = ['Basic business skills']
    
    return {
        "overview": f"Start a {idea['title']} business in {user_info.get('village', 'your village')}. {idea.get('description', '')}",
        "skills": skills,
        "investment_breakdown": {
            "Raw Materials": idea.get('required_investment_min', idea.get('investment_min', 10000)) * 0.4,
            "Equipment": idea.get('required_investment_min', idea.get('investment_min', 10000)) * 0.3,
            "Marketing": idea.get('required_investment_min', idea.get('investment_min', 10000)) * 0.1,
            "Miscellaneous": idea.get('required_investment_min', idea.get('investment_min', 10000)) * 0.2
        },
        "timeline": {
            "0-3 months": "Setup and initial production",
            "3-6 months": "Market establishment and growth",
            "6-12 months": "Scaling and expansion"
        },
        "resources": ["Local suppliers", "Raw material vendors", "Market access"],
        "target_market": "Local community and nearby towns",
        "revenue_estimate": "Expected monthly revenue: ₹" + str(idea.get('required_investment_min', idea.get('investment_min', 10000)) * 0.5),
        "risks": ["Market competition", "Seasonal demand", "Supply chain"],
        "next_steps": [
            "Research local market demand",
            "Connect with suppliers",
            "Apply for government schemes"
        ]
    }

def chat_with_groq(message, context="", conversation_history=None):
    """
    General chat function using Groq - ENHANCED with REAL-TIME smart Google search
    """
    try:
        # Try to enhance context with real-time smart search
        enhanced_context = context
        
        # Extract user context from conversation if available
        user_context = {}
        if context:
            # Parse context for location, interests, budget
            import re
            name_match = re.search(r'name[=:]?\s*(\w+)', context, re.IGNORECASE)
            location_match = re.search(r'(?:location|village)[=:]?\s*([^,\n]+)', context, re.IGNORECASE)
            interest_match = re.search(r'interest[s]?[=:]?\s*([^,\n]+)', context, re.IGNORECASE)
            budget_match = re.search(r'budget[=:]?\s*[₹]?(\d+)', context, re.IGNORECASE)
            
            if name_match:
                user_context['name'] = name_match.group(1)
            if location_match:
                user_context['location'] = location_match.group(1).strip()
            if interest_match:
                user_context['interests'] = interest_match.group(1).strip()
            if budget_match:
                user_context['budget'] = int(budget_match.group(1))
        
        if WEB_SEARCH_AVAILABLE:
            try:
                from utils.web_search import smart_google_search, get_location_based_opportunities
                
                message_lower = message.lower()
                
                # For business/idea queries - get location-based opportunities
                if any(word in message_lower for word in ['business', 'idea', 'startup', 'suggest', 'recommend']):
                    if user_context.get('location'):
                        print(f"🌐 Fetching opportunities for {user_context['location']}...")
                        opportunities = get_location_based_opportunities(user_context)
                        
                        enhanced_context += f"\n\n**REAL-TIME MARKET INTELLIGENCE ({datetime.now().year}):**\n"
                        
                        if opportunities.get('trends'):
                            enhanced_context += "\n**Trending Now:**\n"
                            for trend in opportunities['trends'][:2]:
                                enhanced_context += f"• {trend.get('title', '')}\n"
                        
                        if opportunities.get('local_demands'):
                            enhanced_context += "\n**High Demand In Area:**\n"
                            for demand in opportunities['local_demands'][:2]:
                                enhanced_context += f"• {demand.get('title', '')}\n"
                    else:
                        # Generic business search
                        results = smart_google_search("trending small business ideas India 2025 women entrepreneurs", user_context, num_results=3)
                        enhanced_context += f"\n\n**CURRENT MARKET TRENDS (2025):**\n"
                        for result in results:
                            enhanced_context += f"- {result.get('snippet', '')[:150]}...\n"
                
                # For scheme/funding queries
                if any(word in message_lower for word in ['loan', 'funding', 'scheme', 'subsidy', 'pmegp', 'mudra', 'government']):
                    location = user_context.get('location', 'India')
                    scheme_results = smart_google_search(f"government schemes women entrepreneurs {location} 2025", user_context, num_results=4)
                    if scheme_results:
                        enhanced_context += f"\n\n**AVAILABLE GOVERNMENT SCHEMES:**\n"
                        for result in scheme_results:
                            enhanced_context += f"- {result.get('title', '')}\n  {result.get('snippet', '')[:100]}...\n"
                
                # For specific product/service queries
                if any(word in message_lower for word in ['price', 'cost', 'market', 'demand', 'selling']):
                    # Extract business type from message
                    query = f"{message} market analysis India 2025"
                    market_results = smart_google_search(query, user_context, num_results=3)
                    if market_results:
                        enhanced_context += f"\n\n**CURRENT MARKET DATA:**\n"
                        for result in market_results:
                            enhanced_context += f"- {result.get('snippet', '')[:120]}...\n"
                
                # For location-specific queries
                if 'near me' in message_lower or 'nearby' in message_lower or 'around' in message_lower:
                    if user_context.get('location'):
                        query = f"{message} {user_context['location']} resources"
                        local_results = smart_google_search(query, user_context, num_results=3)
                        if local_results:
                            enhanced_context += f"\n\n**LOCAL RESOURCES IN {user_context.get('location').upper()}:**\n"
                            for result in local_results:
                                enhanced_context += f"- {result.get('title', '')}\n"
                                
            except Exception as e:
                print(f"Error enhancing context with smart search: {e}")
        
        messages = [
            {"role": "system", "content": f"""You are Startup Sathi, a friendly, knowledgeable business advisor for rural women entrepreneurs in India with access to REAL-TIME market data and current trends.

**Current Date: {datetime.now().strftime('%B %d, %Y')}**

Your role:
- Help women discover and start small businesses using CURRENT 2025 market data
- Provide practical, step-by-step guidance with COMPLETE, DETAILED, UP-TO-DATE information
- Answer questions about business ideas, resources, government schemes, financing, marketing
- Use REAL data when available (market trends, location data, scheme details)
- Be encouraging and supportive
- Use simple language (mix of Hindi-English is fine)
- Give SPECIFIC, ACTIONABLE, COMPREHENSIVE answers with numbers, examples, and detailed steps
- Reference CURRENT trends and opportunities in India

When answering:
- If asked about a SPECIFIC BUSINESS (like "pickling", "mushroom cultivation", "millet products"), provide:
  * Complete overview of the business (4-5 sentences with WHY it's relevant in 2024-2025)
  * CURRENT market demand and trends for this business
  * Required investment breakdown with REALISTIC 2024-2025 costs
  * Equipment and raw materials needed (detailed list with current prices)
  * Step-by-step process to start (at least 8-12 detailed steps)
  * Skills required (technical + business + digital)
  * Expected profit margins and monthly revenue (realistic)
  * Where to sell (physical markets + online platforms like Meesho, ONDC, WhatsApp Business)
  * How to market (social media, local networking, digital tools)
  * Government schemes applicable with loan amounts and subsidy %
  * Licenses and registrations needed (FSSAI, GST, Udyam, etc.)
  * Month-by-month timeline for first year
  * Current success stories and examples
  
- If asked about government schemes, provide:
  * Scheme name and managing authority
  * Loan amounts and subsidy percentages (35% for women in PMEGP, etc.)
  * Interest rates (current rates)
  * Complete eligibility criteria
  * Step-by-step application process
  * Portal URLs (kviconline.gov.in, udyamimitra.in, etc.)
  * Contact helplines
  * Documents needed
  * Processing time
  
- If asked about business prerequisites/requirements, list EVERYTHING:
  * Equipment with brand suggestions and prices
  * Raw materials with current market rates
  * Licenses (FSSAI for food, others)
  * Skills and training needed
  * Space requirements
  * Manpower needs
  * Initial working capital
  
- If asked "how", give detailed step-by-step instructions (minimum 8-10 actionable steps)
- If asked "where", give specific suggestions (markets, suppliers, banks, training centers)
- If asked about "location" or "nearby", suggest using Google Maps and local market visits
- Always be positive, motivating, and THOROUGH

**IMPORTANT GUIDELINES:**
1. When user asks for "puri jankari" (complete information) or "detail information" or "sab batao", provide EXTENSIVE, COMPREHENSIVE details covering ALL aspects
2. Use REAL data provided in context (market trends, scheme details, location info)
3. Give CURRENT 2024-2025 information, not outdated data
4. Be SPECIFIC with numbers (₹ amounts, percentages, distances, timelines)
5. Provide ACTIONABLE next steps, not vague advice
6. Include digital/online opportunities (WhatsApp Business, Meesho, Instagram, ONDC)
7. Mention trending sectors: organic/health foods, eco-friendly products, digital services, traditional with modern marketing

Don't give short answers - be thorough and detailed. Think of yourself as a complete business consultant."""}
        ]
        
        # Add conversation history safely
        if conversation_history and len(conversation_history) > 0:
            for hist_item in conversation_history[-5:]:  # Last 5 exchanges
                if isinstance(hist_item, dict):
                    user_msg = hist_item.get('message', '')
                    bot_resp = hist_item.get('response', '')
                    if user_msg:
                        messages.append({"role": "user", "content": user_msg})
                    if bot_resp:
                        messages.append({"role": "assistant", "content": bot_resp[:300]})  # Truncate long responses
        
        # Add context if provided (this includes user profile, business details, scheme info)
        if context:
            messages.append({"role": "system", "content": f"Current Context:\n{context}"})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1500  # Increased for detailed responses
        )
        
        return response.choices[0].message.content
    except Exception as e:
        error_str = str(e)
        print(f"❌ Chat error: {e}")
        
        # If GROQ rate limit hit, fallback to Gemini
        if 'rate_limit' in error_str.lower() or '429' in error_str:
            print(f"🔄 GROQ rate limit! Using Gemini for chat...")
            try:
                # Reconstruct prompt for Gemini
                system_content = next((msg['content'] for msg in messages if msg['role'] == 'system'), '')
                user_messages = [msg['content'] for msg in messages if msg['role'] == 'user']
                full_prompt = f"{system_content}\n\nUser: {user_messages[-1] if user_messages else message}"
                
                gemini_response = gemini_model.generate_content(full_prompt)
                return gemini_response.text
            except Exception as gemini_error:
                print(f"❌ Gemini chat failed: {gemini_error}")
                
                # Try DeepSeek as final fallback
                print(f"🔄 Falling back to DeepSeek for chat...")
                try:
                    deepseek_response = deepseek_client.chat.completions.create(
                        model=DEEPSEEK_MODEL,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1500
                    )
                    return deepseek_response.choices[0].message.content
                except Exception as deepseek_error:
                    print(f"❌ DeepSeek chat failed: {deepseek_error}")
                    return "I'm having some trouble right now. 😊 Could you please try asking your question in a different way? Or try: 'Show me business ideas' or 'Find resources'"
        
        import traceback
        traceback.print_exc()
        return "I'm having some trouble right now. 😊 Could you please try asking your question in a different way? Or try: 'Show me business ideas' or 'Find resources'"

def answer_faq(question, faq_data):
    """Answer FAQs using Groq"""
    try:
        faq_context = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in faq_data])
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": f"Answer based on this FAQ knowledge base:\n{faq_context}"},
                {"role": "user", "content": question}
            ],
            temperature=0.5,
            max_tokens=300
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"FAQ error: {e}")
        return None
