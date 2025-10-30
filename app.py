from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from models import db, User, ChatHistory, BusinessContext
from nlp.intent import detect_intent, extract_entities, categorize_interest
from utils.llm import generate_plan, chat_with_groq, generate_business_ideas, find_local_resources, find_government_schemes
from utils.rag import save_chat_to_rag, save_business_context, build_rag_context_for_query, get_user_conversation_history
import json
from datetime import datetime
import os
import requests

app = Flask(__name__)
# Enable CORS for React frontend with specific configuration
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173","https://ai-for-her.onrender.com"]}})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///startup_sathi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
db.init_app(app)

# Session storage for user context
user_sessions = {}

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Chatbot API is running"}), 200

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    """Main chat endpoint"""
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not user_msg:
            return jsonify({"error": "Empty message"}), 400
        
        # Get or create user session
        if session_id not in user_sessions:
            user_sessions[session_id] = {
                'user_id': None,
                'current_step': 'greeting',
                'context': {},
                'history': []
            }
        
        user_session = user_sessions[session_id]
        
        # Detect intent
        intent = detect_intent(user_msg)
        entities = extract_entities(user_msg)
        
        # Update context with entities - BUT don't overwrite location if already set
        context = user_session['context']
        for key, value in entities.items():
            # Only update location/village if not already set (prevent overwrites)
            if key in ['location', 'village']:
                if not context.get('location') and not context.get('village'):
                    context[key] = value
            else:
                # Update other entities normally
                context[key] = value
        
        # Smart state-based routing: check conversation state
        context = user_session['context']
        
        # DEBUG: Print current state
        print(f"🔍 DEBUG - Message: '{user_msg}'")
        print(f"🔍 DEBUG - Intent: {intent}")
        print(f"🔍 DEBUG - Context: name={context.get('name')}, location={context.get('location')}, village={context.get('village')}, interests={context.get('interests')}")
        print(f"🔍 DEBUG - Entities: {entities}")
        
        # Priority 1: Handle ongoing conversation flow
        if context.get('name') and not context.get('village') and not context.get('location'):
            # We have name but not location - treat any input as location
            if entities.get('location') or (intent == 'general' and len(user_msg.strip()) > 0):
                response = handle_user_info(user_msg, user_session, 'provide_location')
            else:
                response = handle_user_info(user_msg, user_session, intent)
        
        elif context.get('name') and (context.get('village') or context.get('location')) and not context.get('interests'):
            # We have name and location but not interests - check if providing interest
            if intent == 'provide_interest' or entities.get('interests'):
                response = handle_user_info(user_msg, user_session, 'provide_interest')
            elif intent == 'greeting':
                response = handle_greeting(user_msg, user_session)
            elif intent == 'ask_for_ideas':
                response = handle_idea_request(user_msg, user_session)
            elif intent == 'ask_resources':
                response = handle_resource_request(user_msg, user_session)
            elif intent == 'ask_schemes':
                response = handle_scheme_request(user_msg, user_session)
            else:
                # Default to asking for interests if not clear
                response = handle_idea_request(user_msg, user_session)
        
        # Priority 2: Route based on explicit intent
        elif intent == 'greeting':
            # Only show greeting menu if user doesn't have complete profile
            if not context.get('name') or (not context.get('village') and not context.get('location')):
                response = handle_greeting(user_msg, user_session)
            else:
                # User has profile, treat as general query instead
                response = handle_general_query(user_msg, user_session)
        elif intent == 'ask_for_ideas':
            response = handle_idea_request(user_msg, user_session)
        elif intent == 'ask_resources':
            response = handle_resource_request(user_msg, user_session)
        elif intent == 'ask_schemes':
            response = handle_scheme_request(user_msg, user_session)
        elif intent == 'ask_plan':
            response = handle_plan_request(user_msg, user_session)
        elif intent == 'ask_mentor':
            response = handle_mentor_request(user_msg, user_session)
        elif intent in ['provide_name', 'provide_location', 'provide_interest', 'provide_budget']:
            response = handle_user_info(user_msg, user_session, intent)
        else:
            response = handle_general_query(user_msg, user_session)
        
        # Save to history
        user_session['history'].append({
            'message': user_msg,
            'response': response.get('reply', ''),
            'intent': intent,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save to database if user exists - RAG INTEGRATION
        if user_session.get('user_id'):
            # Save chat with entities for RAG
            save_chat_to_rag(
                user_id=user_session['user_id'],
                message=user_msg,
                response=response.get('reply', ''),
                intent=intent,
                entities=entities
            )
        
        # ALWAYS include current context in response for frontend sync
        response['context'] = {
            'name': context.get('name'),
            'location': context.get('location') or context.get('village'),
            'interests': context.get('interests') or context.get('categories'),
            'budget': context.get('budget'),
            'has_ideas': bool(context.get('generated_ideas')),
            'has_plan': bool(context.get('generated_plan'))
        }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"error": "Something went wrong", "reply": "I'm having trouble understanding. Could you try again?"}), 500

def handle_greeting(message, user_session):
    """Handle greeting with AI-generated personalized welcome"""
    context = user_session['context']
    
    if not context.get('name'):
        # AI-generated warm greeting
        greeting_prompt = f"""
You are a warm, encouraging mentor for women entrepreneurs in India (especially rural areas).
A user just greeted you. Create a SHORT, friendly welcome message (2-3 sentences) asking their name.
Be culturally sensitive and encouraging. Don't use emojis excessively.
End with: "What should I call you?"
"""
        greeting = chat_with_groq(greeting_prompt, context="greeting_new_user")
        return {
            "reply": greeting,
            "buttons": [],
            "type": "text_input"
        }
    else:
        # AI-generated personalized menu based on user's context
        menu_prompt = f"""
User name: {context['name']}
Location: {context.get('village') or context.get('location', 'not specified')}
Interests: {context.get('interests', 'not specified')}

Create a SHORT, personalized welcome back message (2-3 sentences) mentioning what you can help them with.
List 4 options: business ideas, local resources, government schemes, mentor connection.
Be encouraging and culturally appropriate for Indian women entrepreneurs.
"""
        menu_message = chat_with_groq(menu_prompt, context=f"welcome_back_{context['name']}")
        
        return {
            "reply": menu_message,
            "buttons": [
                {"text": "🔍 Business Ideas", "value": "show_ideas"},
                {"text": "📍 Local Resources", "value": "find_resources"},
                {"text": "💰 Government Schemes", "value": "show_schemes"},
                {"text": "👥 Mentor Connection", "value": "request_mentor"}
            ],
            "type": "button_choice"
        }

def handle_idea_request(message, user_session):
    """Handle business idea suggestions - FULLY AI-DRIVEN with smart questioning"""
    context = user_session['context']
    
    # Step 1: Check if we need to ask about interests
    if not context.get('interests') and not context.get('categories'):
        # AI-generated interest question
        interest_prompt = f"""
User: {context.get('name', 'Friend')}
Location: {context.get('village') or context.get('location', 'their area')}

As a mentor, ask them about their interests/skills in a warm, conversational way (2-3 sentences).
Then present 8 interest categories as buttons.
Be encouraging and mention that there's no wrong answer.
"""
        interest_msg = chat_with_groq(interest_prompt, context="asking_interests")
        
        return {
            "reply": interest_msg,
            "buttons": [
                {"text": "🍳 Cooking & Food", "value": "food"},
                {"text": "🧵 Sewing & Tailoring", "value": "tailoring"},
                {"text": "🐄 Dairy & Livestock", "value": "dairy"},
                {"text": "🌾 Farming & Agriculture", "value": "agriculture"},
                {"text": "💄 Beauty Services", "value": "beauty"},
                {"text": "🎨 Handicrafts & Art", "value": "handicraft"},
                {"text": "📚 Teaching & Education", "value": "education"},
                {"text": "🏪 Retail & Shop", "value": "retail"}
            ],
            "type": "button_choice"
        }
    
    # Step 2: Check if we need budget information
    if not context.get('budget') and context.get('interests'):
        # AI-generated budget question
        budget_prompt = f"""
User: {context['name']}
Interest: {context['interests']}

As their mentor, ask about their investment capacity in an encouraging, non-judgmental way (2-3 sentences).
Mention that even small amounts can start good businesses.
"""
        budget_msg = chat_with_groq(budget_prompt, context="asking_budget")
        
        return {
            "reply": budget_msg,
            "buttons": [
                {"text": "Under ₹10,000", "value": "budget_10000"},
                {"text": "₹10,000 - ₹50,000", "value": "budget_50000"},
                {"text": "₹50,000 - ₹1,00,000", "value": "budget_100000"},
                {"text": "Above ₹1,00,000", "value": "budget_200000"}
            ],
            "type": "button_choice"
        }
    
    # Step 3: Check if ideas already generated - return them with AI explanation
    if context.get('generated_ideas'):
        ideas = context['generated_ideas']
        
        # AI-generated explanation of why these ideas were selected
        explanation_prompt = f"""
User profile:
- Name: {context['name']}
- Location: {context.get('village') or context.get('location')}
- Interest: {context.get('interests')}
- Budget: ₹{context.get('budget')}

Generated {len(ideas)} business ideas for them.

Create a SHORT (3-4 sentences) explanation of:
1. How you analyzed their profile
2. Why these ideas match their situation
3. Encourage them to explore each idea

Be warm, encouraging, and specific to their profile.
"""
        explanation = chat_with_groq(explanation_prompt, context="ideas_explanation")
        
        return {
            "reply": explanation,
            "ideas": ideas,
            "type": "idea_list",
            "message": "Click any idea to see full details, or select one to create a complete business plan!"
        }
    
    # Step 4: Generate ideas using AI with RAG context
    user_info = {
        'name': context.get('name', 'User'),
        'village': context.get('village') or context.get('location', 'Your area'),
        'interests': context.get('interests', ''),
        'budget': context.get('budget', 50000)
    }
    
    # Build RAG context if user exists
    rag_context = ""
    if user_session.get('user_id'):
        rag_context = build_rag_context_for_query(
            user_id=user_session['user_id'],
            location=user_info['village'],
            current_message=message
        )
    
    # Generate loading message using AI
    loading_prompt = f"""
User: {user_info['name']}
Interest: {user_info['interests']}
Budget: ₹{user_info['budget']}
Location: {user_info['village']}

Create a SHORT (2 sentences) "analyzing" message telling them you're researching the best business opportunities.
Be encouraging and mention you're checking market trends.
"""
    loading_msg = chat_with_groq(loading_prompt, context="generating_ideas")
    
    print(f"🤖 Generating ideas for: {user_info}")
    print(f"📚 RAG Context: {len(rag_context)} chars")
    
    # Generate ideas with AI
    ideas = generate_business_ideas(user_info, rag_context=rag_context)
    
    if not ideas or len(ideas) == 0:
        # AI-generated error message
        error_prompt = f"""
Technical issue: couldn't generate business ideas.
User: {user_info['name']}, interested in {user_info['interests']}, budget ₹{user_info['budget']}

Create an apologetic message (2-3 sentences) and suggest trying again.
Be warm and reassuring.
"""
        error_msg = chat_with_groq(error_prompt, context="idea_generation_error")
        
        return {
            "reply": error_msg,
            "type": "text",
            "buttons": [{"text": "🔄 Try Again", "value": "show_ideas"}]
        }
    
    # Format ideas for display
    formatted_ideas = []
    for idx, idea in enumerate(ideas):
        formatted_ideas.append({
            'id': idx,
            'title': idea.get('title', 'Business Idea'),
            'description': idea.get('description', ''),
            'required_investment_min': idea.get('investment_min', 0),
            'required_investment_max': idea.get('investment_max', 0),
            'skills_required': idea.get('skills', ''),
            'suitability': idea.get('suitability', ''),
            'market_size': idea.get('market_size', ''),
            'profitability': idea.get('profitability', ''),
            'home_based': idea.get('home_based', False),
            'competition_level': idea.get('competition_level', 'Unknown'),
            'why_this_location': idea.get('why_this_location', ''),
            'funding_suggestion': idea.get('funding_suggestion', ''),
            'actual_realistic_cost': idea.get('actual_realistic_cost', '')
        })
    
    # Store ideas in context AND database (RAG)
    context['generated_ideas'] = formatted_ideas
    
    if user_session.get('user_id'):
        save_business_context(
            user_id=user_session['user_id'],
            context_type='ideas',
            content=formatted_ideas,
            location=user_info['village']
        )
    
    # AI-generated explanation
    explanation_prompt = f"""
Successfully generated {len(formatted_ideas)} business ideas for:
- {user_info['name']} from {user_info['village']}
- Interest: {user_info['interests']}
- Budget: ₹{user_info['budget']}

Create an exciting announcement (3-4 sentences) that:
1. Congratulates them
2. Mentions how the ideas were personalized
3. Encourages them to explore each one
4. Mentions next steps (click for details, select to plan)

Be warm, encouraging, culturally appropriate.
"""
    explanation = chat_with_groq(explanation_prompt, context="ideas_generated_success")
    
    return {
        "reply": explanation,
        "ideas": formatted_ideas,
        "type": "idea_list",
        "context": context
    }

def handle_resource_request(message, user_session):
    """Handle nearby resources request - FULLY AI-DRIVEN"""
    context = user_session['context']
    
    # Check if location available
    if not context.get('location') and not context.get('village'):
        # AI asks for location
        prompt = f"""
User {context.get('name', 'friend')} wants to find local resources but hasn't shared their location.
Ask for their city/village name in a warm, helpful way (2-3 sentences).
Mention why location is important for finding nearby suppliers.
"""
        reply = chat_with_groq(prompt, context="asking_location_resources")
        return {"reply": reply, "type": "text_input"}
    
    # Check if they have selected a business idea
    if not context.get('budget'):
        # Need to complete profile first
        prompt = f"""
User {context['name']} from {context.get('village') or context.get('location')} wants resources.
But we need to know their business type first. Ask about their investment capacity warmly (2-3 sentences).
"""
        reply = chat_with_groq(prompt, context="need_budget_for_resources")
        return {
            "reply": reply,
            "buttons": [
                {"text": "Under ₹10,000", "value": "budget_10000"},
                {"text": "₹10,000 - ₹50,000", "value": "budget_50000"},
                {"text": "₹50,000 - ₹1,00,000", "value": "budget_100000"},
                {"text": "Above ₹1,00,000", "value": "budget_200000"}
            ],
            "type": "button_choice"
        }
    
    location = context.get('village') or context.get('location')
    business_type = context.get('selected_idea_title', context.get('interests', 'small business'))
    
    # Generate resource information using AI
    resources_data = find_local_resources(location, business_type)
    
    resource_list = []
    
    # Format suppliers
    if 'suppliers' in resources_data:
        for supplier in resources_data['suppliers'][:5]:
            if isinstance(supplier, dict):
                resource_list.append({
                    'name': supplier.get('name', supplier),
                    'type': 'supplier',
                    'address': supplier.get('address', f'Available in {location}'),
                    'details': supplier.get('details', '')
                })
            else:
                resource_list.append({
                    'name': str(supplier),
                    'type': 'supplier',
                    'address': f'Available in {location}',
                    'details': ''
                })
    
    # Format markets
    if 'markets' in resources_data:
        for market in resources_data['markets'][:5]:
            if isinstance(market, dict):
                resource_list.append({
                    'name': market.get('name', market),
                    'type': 'market',
                    'address': market.get('address', f'{location}'),
                    'details': market.get('details', '')
                })
            else:
                resource_list.append({
                    'name': str(market),
                    'type': 'market',
                    'address': f'{location}',
                    'details': ''
                })
    
    # Format government offices
    if 'government_offices' in resources_data:
        for office in resources_data['government_offices'][:3]:
            if isinstance(office, dict):
                resource_list.append({
                    'name': office.get('name', office),
                    'type': 'government',
                    'address': office.get('address', f'{location}'),
                    'details': office.get('details', '')
                })
            else:
                resource_list.append({
                    'name': str(office),
                    'type': 'government',
                    'address': f'{location}',
                    'details': ''
                })
    
    # Add raw materials info if available
    if 'raw_materials' in resources_data:
        info_text = "**Where to find raw materials:**\n"
        for material in resources_data['raw_materials'][:3]:
            info_text += f"• {material}\n"
        context['raw_materials_info'] = info_text
    
    # AI generates personalized resource explanation
    resource_prompt = f"""
Found {len(resource_list)} resources near {location} for {business_type} business.
User: {context['name']}

Create a helpful explanation (3-4 sentences):
1. Summarize what resources were found
2. Explain how these can help their business
3. Encourage them to visit/contact these places
4. Mention what else you can help with

Be practical and encouraging.
"""
    explanation = chat_with_groq(resource_prompt, context=f"resources_{location}")
    
    return {
        "reply": explanation,
        "resources": resource_list,
        "type": "resource_list",
        "additional_info": resources_data.get('info', '')
    }

def handle_scheme_request(message, user_session):
    """Handle government schemes - 100% DYNAMIC based on user's business and situation"""
    context = user_session['context']
    
    # Check if we have enough profile information
    if not context.get('village') and not context.get('location'):
        prompt = f"""
User {context.get('name', 'friend')} wants to know about government schemes.
Ask for their location warmly (2-3 sentences) mentioning schemes vary by state.
"""
        reply = chat_with_groq(prompt, context="need_location_schemes")
        return {"reply": reply, "type": "text_input"}
    
    # Get user info
    user_info = {
        'name': context.get('name', 'Entrepreneur'),
        'village': context.get('village') or context.get('location', 'India'),
        'interests': context.get('interests', 'business'),
        'budget': context.get('budget', 50000)
    }
    
    business_type = context.get('selected_idea_title', context.get('interests', 'small business'))
    
    print(f"🔍 Fetching schemes for: {business_type}, Budget: ₹{user_info['budget']}, Location: {user_info['village']}")
    
    # Fetch schemes using AI + web search (from llm.py)
    schemes = find_government_schemes(user_info, business_type)
    
    # Format schemes for display
    scheme_list = []
    if schemes and len(schemes) > 0:
        for idx, scheme in enumerate(schemes):
            scheme_list.append({
                'id': idx,
                'title': scheme.get('name', 'Government Scheme'),
                'region': scheme.get('region', 'All India'),
                'eligibility': scheme.get('eligibility', 'Women entrepreneurs'),
                'benefit': scheme.get('benefits', ''),
                'apply_link': scheme.get('apply_link', 'https://www.india.gov.in'),
                'documents': scheme.get('documents', 'Aadhaar, PAN, Business Plan'),
                'how_to_apply': scheme.get('how_to_apply', 'Visit government office'),
                'category': scheme.get('category', 'finance')
            })
    
    # If no schemes found or error, AI explains general process
    if not scheme_list:
        print("⚠️ No schemes found, generating AI explanation")
        prompt = f"""
User Profile:
- Name: {user_info['name']}
- Location: {user_info['village']}
- Business: {business_type}
- Budget: ₹{user_info['budget']}

Couldn't fetch live scheme data. Explain HOW to find government schemes:
1. Visit local KVIC/DIC office in their area
2. Mention common schemes (PMEGP, Mudra) but explain they need to check eligibility
3. Suggest searching "government schemes for {business_type} in {user_info['village']}" online
4. Mention visiting banks for Mudra loans
5. Encourage them to ask at Block Development Office

Be helpful, specific to their business and budget. 5-6 sentences. Don't give hardcoded scheme details.
"""
        reply = chat_with_groq(prompt, context=f"scheme_guidance_{business_type}")
        return {
            "reply": reply,
            "type": "text",
            "buttons": [
                {"text": "🔍 Show Business Ideas", "value": "show_ideas"},
                {"text": "📍 Find Resources", "value": "find_resources"}
            ]
        }
    
    # AI generates personalized explanation about the found schemes
    scheme_prompt = f"""
Found {len(scheme_list)} government schemes for:
- User: {user_info['name']} from {user_info['village']}
- Business: {business_type}
- Budget: ₹{user_info['budget']}

Schemes available: {', '.join([s['title'] for s in scheme_list])}

Create helpful explanation (3-4 sentences):
1. Congratulate them for exploring schemes
2. Explain how these specific schemes can help their {business_type} business
3. Mention which scheme matches their ₹{user_info['budget']} budget best
4. Encourage to check eligibility details in the panel

Be encouraging, use simple language suitable for Indian women entrepreneurs.
"""
    explanation = chat_with_groq(scheme_prompt, context=f"schemes_{business_type}")
    
    return {
        "reply": explanation,
        "schemes": scheme_list,
        "type": "scheme_list",
        "message": "Review each scheme's details in the Information Panel →"
    }

def handle_plan_request(message, user_session):
    """Generate startup plan - FULLY DYNAMIC"""
    context = user_session['context']
    
    # Check if idea is selected
    if not context.get('selected_idea_id') is not None and not context.get('selected_idea_title'):
        return {
            "reply": "Please select a business idea first. Would you like me to suggest some ideas?",
            "buttons": [
                {"text": "Yes, show me ideas", "value": "show_ideas"},
                {"text": "I have my own idea", "value": "custom_idea"}
            ],
            "type": "button_choice"
        }
    
    # Get idea from session
    selected_idea = None
    if context.get('selected_idea_id') is not None and context.get('generated_ideas'):
        selected_idea = context['generated_ideas'][context['selected_idea_id']]
    
    if not selected_idea and context.get('selected_idea_title'):
        selected_idea = {
            'title': context['selected_idea_title'],
            'description': context.get('selected_idea_description', ''),
            'required_investment_min': context.get('budget', 10000),
            'required_investment_max': context.get('budget', 50000) * 2,
            'skills_required': 'Basic business skills'
        }
    
    if not selected_idea:
        return {
            "reply": "Let me first understand what business you want to start. What type of business interests you?",
            "type": "text_input"
        }
    
    idea_dict = {
        'id': selected_idea.get('id', 0),
        'title': selected_idea.get('title', 'Your Business'),
        'description': selected_idea.get('description', ''),
        'required_investment_min': selected_idea.get('required_investment_min', 0),
        'required_investment_max': selected_idea.get('required_investment_max', 0),
        'skills_required': selected_idea.get('skills_required', '')
    }
    
    # Generate plan using Groq
    user_info = {
        'name': context.get('name', 'User'),
        'village': context.get('village') or context.get('location', 'Your Village'),
        'interests': context.get('interests', ''),
        'budget': context.get('budget', 'Not specified')
    }
    
    plan_json = generate_plan(idea_dict, user_info)
    
    # Store in context
    context['current_plan'] = plan_json
    
    return {
        "reply": f"Great! Here's your detailed startup plan for **{idea_dict['title']}**:",
        "plan": plan_json,
        "type": "plan_display",
        "buttons": [
            {"text": "📍 Find Resources", "value": "find_resources"},
            {"text": "💰 View Schemes", "value": "show_schemes"},
            {"text": "👥 Talk to Mentor", "value": "request_mentor"}
        ]
    }

def handle_mentor_request(message, user_session):
    """Handle mentor connection request - FULLY DYNAMIC"""
    context = user_session['context']
    
    if not context.get('name'):
        return {
            "reply": "I'd love to connect you with a mentor! First, please tell me your name.",
            "type": "text_input"
        }
    
    if not context.get('phone'):
        return {
            "reply": "Please provide your phone number so a mentor can contact you:",
            "type": "text_input"
        }
    
    # Store mentor request in session
    mentor_request = {
        'user_name': context.get('name', 'User'),
        'phone': context.get('phone', ''),
        'business_idea': context.get('selected_idea_title', 'Business'),
        'location': context.get('location', 'Not specified'),
        'notes': message,
        'requested_at': datetime.now().isoformat()
    }
    
    context['mentor_request'] = mentor_request
    
    return {
        "reply": f"Perfect! I've registered your request, {context['name']}.\n\n"
                 f"A mentor will contact you on {context.get('phone', 'your number')} within 2-3 business days.\n\n"
                 f"In the meantime, you can:\n"
                 f"• Explore more business ideas\n"
                 f"• Find local resources\n"
                 f"• Learn about government schemes\n\n"
                 f"Is there anything else I can help you with?",
        "type": "success",
        "buttons": [
            {"text": "🔍 Explore Ideas", "value": "show_ideas"},
            {"text": "📍 Find Resources", "value": "find_resources"},
            {"text": "💰 View Schemes", "value": "show_schemes"}
        ]
    }

def handle_user_info(message, user_session, intent):
    """Handle user information collection"""
    context = user_session['context']
    entities = extract_entities(message)
    
    if intent == 'provide_name' or entities.get('name'):
        name = entities.get('name', message.strip())
        context['name'] = name
        
        # Create or update user
        user = User.query.filter_by(name=name).first()
        if not user:
            user = User(name=name)
            db.session.add(user)
            db.session.commit()
        user_session['user_id'] = user.id
        
        return {
            "reply": f"Nice to meet you, {name}! 😊 Which village or city are you from?",
            "type": "text_input"
        }
    
    elif intent == 'provide_location' or entities.get('location'):
        location = entities.get('location', message.strip())
        
        # Filter out button phrases that shouldn't be stored as location
        invalid_locations = ['let me tell you my city', 'share my location', 'my city', 'my village', 'my location']
        if location.lower() in invalid_locations:
            return {
                "reply": "Please type your city or village name (for example: Mumbai, Nashik, Pune, etc.)",
                "type": "text_input"
            }
        
        context['village'] = location
        context['location'] = location  # Store location string
        
        # Update user
        if user_session.get('user_id'):
            user = User.query.get(user_session['user_id'])
            if user:
                user.village = location
                db.session.commit()
        
        return {
            "reply": f"Perfect! 📍 You're from **{location}**.\n\nNow, what are you interested in? What do you enjoy doing or what skills do you have?",
            "buttons": [
                {"text": "🍳 Cooking & Food", "value": "interest_cooking"},
                {"text": "🧵 Sewing & Tailoring", "value": "interest_sewing"},
                {"text": "🐄 Dairy & Animals", "value": "interest_animals"},
                {"text": "🌾 Farming & Agriculture", "value": "interest_farming"},
                {"text": "💄 Beauty & Salon", "value": "interest_beauty"},
                {"text": "🎨 Handicrafts & Art", "value": "interest_crafts"},
                {"text": "📚 Teaching & Tutoring", "value": "interest_teaching"},
                {"text": "🏪 Shop & Retail", "value": "interest_retail"}
            ],
            "type": "button_choice"
        }
    
    elif intent == 'provide_interest':
        interests = message.strip()
        context['interests'] = interests
        context['categories'] = categorize_interest(interests)
        
        # Update user
        if user_session.get('user_id'):
            user = User.query.get(user_session['user_id'])
            if user:
                user.interests = interests
                db.session.commit()
        
        return handle_idea_request(message, user_session)
    
    elif intent == 'provide_budget' or entities.get('budget'):
        budget = entities.get('budget', 50000)
        context['budget'] = budget
        
        return handle_idea_request(message, user_session)
    
    return handle_general_query(message, user_session)

def handle_general_query(message, user_session):
    """
    Handle general queries - SMART CONVERSATIONAL AI
    - Understands "I want to start X business"
    - Asks follow-up questions
    - Provides contextual answers
    - Guides user through the process
    """
    try:
        context = user_session['context']
        history = user_session['history'][-5:]  # Last 5 exchanges
        message_lower = message.lower()
        
        print(f"🔍 DEBUG handle_general_query: message='{message}'")
        print(f"🔍 DEBUG context: generated_ideas={len(context.get('generated_ideas', []))} items")
        
        # FIRST: Check if user is trying to select a specific business from generated ideas
        if context.get('generated_ideas'):
            for idea in context['generated_ideas']:
                idea_title = idea['title'].lower()
                idea_title_clean = idea_title.replace(' business', '').replace(' service', '').strip()
                message_clean = message_lower.replace(' business', '').replace(' service', '').strip()
                
                print(f"🔍 Checking match: '{idea_title_clean}' vs '{message_clean}'")
                
                # Match various patterns: "I want to start X", "Tell me about X", "X business", etc.
                # More aggressive matching
                title_words = [word for word in idea_title_clean.split() if len(word) > 3]
                match_count = sum(1 for word in title_words if word in message_clean)
                
                # Check if it's a match
                is_match = (
                    idea_title_clean in message_clean or 
                    match_count >= max(1, len(title_words) / 2) or  # Match at least half the significant words
                    any(word in message_clean for word in title_words if len(word) > 5)  # Match any long word
                )
                
                if is_match:
                    print(f"✅ MATCHED BUSINESS: {idea['title']}")
                    
                    # AUTO-SELECT THIS BUSINESS
                    context['selected_idea_id'] = idea['id']
                    context['selected_idea_title'] = idea['title']
                    context['selected_idea_description'] = idea['description']
                    context['selected_idea_investment_min'] = idea.get('required_investment_min', 0)
                    context['selected_idea_investment_max'] = idea.get('required_investment_max', 0)
                    context['selected_idea_skills'] = idea.get('skills_required', '')
                    context['selected_idea_suitability'] = idea.get('suitability', '')
                    
                    # Check if user wants to START or just get INFO
                    if any(word in message_lower for word in ['start', 'begin', 'launch', 'open', 'want to', 'plan', 'chalu', 'shuru']):
                        # User wants to START this business - generate plan immediately
                        print(f"🚀 User wants to START business: {idea['title']}")
                        
                        # Show immediate feedback
                        immediate_response = {
                            "reply": f"✅ **Excellent choice, {context.get('name', '')}!**\n\n🎯 Selected: **{idea['title']}**\n\n⏳ I'm creating your complete startup plan with:\n• Step-by-step timeline\n• Investment breakdown\n• Revenue projections\n• Where to buy and sell\n• Risk analysis\n\nPlease wait a moment...",
                            "type": "text"
                        }
                        
                        try:
                            user_info = {
                                'name': context.get('name', 'User'),
                                'village': context.get('village') or context.get('location', 'Your area'),
                                'interests': context.get('interests', ''),
                                'budget': context.get('budget', 50000)
                            }
                            
                            print(f"📋 Generating plan for {idea['title']}...")
                            plan = generate_plan(idea, user_info)
                            context['current_plan'] = plan
                            
                            print(f"✅ Plan generated successfully!")
                            
                            return {
                                "reply": f"🎉 **Your {idea['title']} Business Plan is Ready!**\n\n📋 I've created a complete startup plan for you. Check the information panel on the right →\n\nThe plan includes everything you need to get started!",
                                "plan": plan,
                                "type": "plan_display",
                                "buttons": [
                                    {"text": "📍 Find Nearby Resources", "value": "find_resources"},
                                    {"text": "💰 Government Schemes", "value": "show_schemes"},
                                    {"text": "❓ Ask Me Anything", "value": "general_help"}
                                ]
                            }
                        except Exception as plan_error:
                            print(f"❌ Error generating plan: {plan_error}")
                            import traceback
                            traceback.print_exc()
                            
                            return {
                                "reply": f"✅ Selected: **{idea['title']}**\n\n⚠️ I'm having trouble generating the complete plan right now.\n\n**What I can help you with immediately:**\n\n💰 **Investment:** ₹{idea.get('required_investment_min', 0):,} - ₹{idea.get('required_investment_max', 0):,}\n\n🎓 **Skills Needed:** {idea.get('skills_required', 'Basic skills')}\n\n📝 **Overview:** {idea['description'][:200]}...\n\nLet me try creating your plan again, or I can help you with:",
                                "type": "text",
                                "buttons": [
                                    {"text": "� Try Creating Plan Again", "value": "create_plan"},
                                    {"text": "📍 Find Resources Now", "value": "find_resources"},
                                    {"text": "💰 View Schemes", "value": "show_schemes"}
                                ]
                            }
                    
                    else:
                        # User wants INFO about this business
                        print(f"ℹ️ User wants INFO about: {idea['title']}")
                        return {
                            "reply": f"""
🎯 **{idea['title']}**

{idea['description']}

💰 **Investment Needed:** ₹{idea.get('required_investment_min', 0):,} - ₹{idea.get('required_investment_max', 0):,}

🎓 **Skills Required:** {idea.get('skills_required', 'Basic skills')}

✅ **Why Perfect for You:** {idea.get('suitability', 'Matches your profile')}

---

**What would you like to do next?**
""",
                            "type": "text",
                            "buttons": [
                                {"text": "✅ Start This Business", "value": f"I want to start {idea['title']}"},
                                {"text": "📋 Get Full Plan", "value": "create_plan"},
                                {"text": "📍 Find Resources", "value": "find_resources"},
                                {"text": "💰 View Schemes", "value": "show_schemes"},
                                {"text": "🔍 See Other Ideas", "value": "show_ideas"}
                            ]
                        }
    except Exception as e:
        print(f"❌ Error in handle_general_query (business matching): {e}")
        import traceback
        traceback.print_exc()
    
    # SECOND: If user has selected business, answer questions about it
    try:
        if context.get('selected_idea_title'):
            print(f"💼 User has selected business: {context['selected_idea_title']}")
            
            # Simple rule-based response without AI dependency
            selected_business = context['selected_idea_title']
            
            # Check what user is asking about
            if 'how' in message_lower and ('start' in message_lower or 'begin' in message_lower):
                ai_response = f"To start your **{selected_business}** business:\n\n1. Get necessary licenses and registrations\n2. Arrange equipment and raw materials\n3. Set up your workspace\n4. Start marketing to local customers\n5. Begin operations\n\nWould you like to see the complete startup plan with timeline and costs?"
            elif 'investment' in message_lower or 'money' in message_lower or 'cost' in message_lower or 'paisa' in message_lower:
                inv_min = context.get('selected_idea_investment_min', 0)
                inv_max = context.get('selected_idea_investment_max', 0)
                ai_response = f"💰 **Investment for {selected_business}:**\n\n₹{inv_min:,} - ₹{inv_max:,}\n\nThis includes:\n• Equipment & tools\n• Raw materials\n• Marketing expenses\n• Initial working capital\n\nWould you like to see the detailed breakdown?"
            elif 'where' in message_lower and ('sell' in message_lower or 'market' in message_lower):
                ai_response = f"🛍️ **Where to sell your {selected_business} products:**\n\n• Local markets and shops\n• Online platforms (social media, e-commerce)\n• Direct to customers (door-to-door)\n• Bulk orders to businesses\n\nWant to find nearby markets and suppliers?"
            elif 'scheme' in message_lower or 'loan' in message_lower or 'government' in message_lower:
                ai_response = f"💰 **Government schemes for {selected_business}:**\n\n• PMEGP (Prime Minister Employment Generation Programme)\n• Mudra Loan (up to ₹10 lakh)\n• Stand-Up India Scheme\n• State-specific entrepreneurship schemes\n\nClick 'View Schemes' to see complete details!"
            elif 'skill' in message_lower or 'training' in message_lower:
                skills = context.get('selected_idea_skills', 'Basic business skills')
                ai_response = f"🎓 **Skills for {selected_business}:**\n\n{skills}\n\n**Where to get training:**\n• Local vocational training centers\n• Government skill development programs\n• Online courses and tutorials\n• Experienced mentors in your area"
            else:
                # Generic response about the business
                ai_response = f"I'm here to help with your **{selected_business}** business! 😊\n\n**Ask me about:**\n• How to start?\n• Investment needed?\n• Where to sell?\n• Government schemes?\n• Required skills?\n• Complete business plan?\n\nWhat would you like to know?"
            
            # Add helpful buttons based on conversation
            buttons = []
            if 'scheme' in message_lower or 'loan' in message_lower or 'government' in message_lower:
                buttons.append({"text": "💰 View All Schemes", "value": "show_schemes"})
            if 'where' in message_lower or 'resource' in message_lower or 'supplier' in message_lower or 'market' in message_lower:
                buttons.append({"text": "📍 Find Nearby Resources", "value": "find_resources"})
            if not context.get('current_plan'):
                buttons.append({"text": "📋 Get Full Startup Plan", "value": "create_plan"})
            
            return {
                "reply": ai_response,
                "type": "text",
                "buttons": buttons if buttons else [
                    {"text": "📋 Get Startup Plan", "value": "create_plan"},
                    {"text": "📍 Find Resources", "value": "find_resources"},
                    {"text": "💰 View Schemes", "value": "show_schemes"}
                ]
            }
    except Exception as e:
        print(f"❌ Error in handle_general_query (selected business): {e}")
        import traceback
        traceback.print_exc()
    
    # THIRD: If user has ideas but hasn't selected, guide them
    try:
        if context.get('generated_ideas'):
            # Check if they're asking for details
            if any(keyword in message_lower for keyword in ['detail', 'complete', 'full', 'more', 'tell me', 'explain', 'batao', 'jankari']):
                ideas = context['generated_ideas']
                detailed_info = f"📋 **Here are your personalized business ideas:**\n\n"
                
                for idx, idea in enumerate(ideas, 1):
                    detailed_info += f"**{idx}. {idea['title']}**\n"
                    detailed_info += f"{idea['description'][:150]}...\n"
                    detailed_info += f"💰 Investment: ₹{idea['required_investment_min']:,} - ₹{idea['required_investment_max']:,}\n\n"
                
                detailed_info += "\n**To get started, tell me which business you like!**\n"
                detailed_info += "For example: 'I want to start [business name]'\n"
                detailed_info += "Or click 'Select & Plan' button on any business card in the right panel."
                
                return {
                    "reply": detailed_info,
                    "type": "text",
                    "buttons": [
                        {"text": f"▶ {ideas[0]['title'][:25]}", "value": f"I want to start {ideas[0]['title']}"} if len(ideas) > 0 else None,
                        {"text": f"▶ {ideas[1]['title'][:25]}", "value": f"I want to start {ideas[1]['title']}"} if len(ideas) > 1 else None,
                        {"text": "🔍 View All Ideas Again", "value": "show_ideas"}
                    ]
                }
            
            # Simple fallback without AI
            print(f"💬 Simple response for: {message}")
            return {
                "reply": f"I have {len(context['generated_ideas'])} great business ideas for you!\n\n**To see full details:**\n• Click on any business card in the right panel\n• Or ask me: 'Tell me about [business name]'\n\n**To create a startup plan:**\n• Click the 'Select & Plan ➜' button on any card\n• Or tell me: 'I want to start [business name]'\n\nWhich business interests you the most?",
                "type": "text",
                "buttons": [
                    {"text": "🔍 View All Ideas", "value": "show_ideas"},
                    {"text": "📍 Find Resources", "value": "find_resources"}
                ]
            }
    except Exception as e:
        print(f"❌ Error in handle_general_query (ideas not selected): {e}")
        import traceback
        traceback.print_exc()
    
    # FOURTH: User hasn't generated ideas yet - guide them
    try:
        print(f"💬 User hasn't generated ideas, providing guidance")
        
        # Simple rule-based response
        if not context.get('name'):
            ai_response = "Hello! I'm Startup Sathi, your business guide. 😊\n\nWhat's your name?"
        elif not context.get('location') and not context.get('village'):
            ai_response = f"Nice to meet you, {context.get('name')}! 😊\n\nWhich village or city are you from?"
        elif not context.get('interests'):
            ai_response = "Great! Let me help you find the perfect business idea. 💡\n\nWhat are you interested in? (cooking, beauty, handicrafts, farming, teaching, etc.)"
        elif not context.get('budget'):
            ai_response = "Perfect! 👍 Now, how much money can you invest to start your business?\n\n• Under ₹10,000\n• ₹10,000 - ₹50,000\n• ₹50,000 - ₹1,00,000\n• Above ₹1,00,000"
        else:
            ai_response = "I have all your information! Let me show you perfect business ideas based on your profile. 🎉"
        
        # Provide helpful buttons based on what's missing
        buttons = []
        if not context.get('interests'):
            buttons.append({"text": "🎯 Tell Me My Interests", "value": "show_ideas"})
        else:
            buttons.append({"text": "🔍 Show Business Ideas", "value": "show_ideas"})
        
        buttons.append({"text": "📍 Find Local Resources", "value": "find_resources"})
        buttons.append({"text": "💰 Government Schemes", "value": "show_schemes"})
        
        return {
            "reply": ai_response,
            "type": "text",
            "buttons": buttons
        }
    except Exception as e:
        print(f"❌ Error in handle_general_query (final fallback): {e}")
        import traceback
        traceback.print_exc()
        
        # Ultimate fallback
        return {
            "reply": "I'm here to help you start your business! 😊\n\nWhat would you like to do?",
            "type": "text",
            "buttons": [
                {"text": "🔍 Show Business Ideas", "value": "show_ideas"},
                {"text": "📍 Find Resources", "value": "find_resources"},
                {"text": "💰 Government Schemes", "value": "show_schemes"}
            ]
        }

@app.route('/api/select_idea', methods=['POST'])
def select_idea():
    """Select a business idea and store full context, then return plan immediately"""
    try:
        data = request.json
        idea_id = data.get('idea_id')
        session_id = data.get('session_id', 'default')
        
        if session_id not in user_sessions:
            return jsonify({"error": "Session not found"}), 404
        
        context = user_sessions[session_id]['context']
        context['selected_idea_id'] = idea_id
        
        # Store full idea details in context for future reference
        selected_idea = None
        if context.get('generated_ideas'):
            for idea in context['generated_ideas']:
                if idea['id'] == idea_id:
                    selected_idea = idea
                    context['selected_idea_title'] = idea['title']
                    context['selected_idea_description'] = idea['description']
                    context['selected_idea_investment_min'] = idea.get('required_investment_min', 0)
                    context['selected_idea_investment_max'] = idea.get('required_investment_max', 0)
                    context['selected_idea_skills'] = idea.get('skills_required', '')
                    context['selected_idea_suitability'] = idea.get('suitability', '')
                    break
        
        if not selected_idea:
            return jsonify({"error": "Idea not found"}), 404
        
        # IMMEDIATELY generate and return the plan
        user_info = {
            'name': context.get('name', 'User'),
            'village': context.get('village') or context.get('location', 'Your area'),
            'interests': context.get('interests', ''),
            'budget': context.get('budget', 50000)
        }
        
        # Generate plan using AI
        plan = generate_plan(selected_idea, user_info)
        
        # Store plan in context
        context['current_plan'] = plan
        context['current_step'] = 'plan_created'
        
        # Also show in chat what was selected
        chat_message = f"""
✅ **Selected: {selected_idea['title']}**

📋 I'm creating a complete startup plan for you...

**What you'll get:**
• Complete business overview
• Investment breakdown
• Step-by-step timeline
• Required skills and resources
• Revenue projections
• Risk analysis
• Immediate next steps

Please check the **Information Panel** on the right →
"""
        
        return jsonify({
            "success": True,
            "reply": chat_message,
            "plan": plan,
            "type": "plan_display",
            "message": f"Complete startup plan for {selected_idea['title']} is ready!"
        })
    
    except Exception as e:
        print(f"Error selecting idea: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/button_click', methods=['POST'])
def button_click():
    """Handle button clicks"""
    try:
        data = request.json
        value = data.get('value', '')
        session_id = data.get('session_id', 'default')
        
        # Map button values to messages
        message_map = {
            'show_ideas': 'I want to see business ideas',
            'find_resources': 'Find resources near me',
            'show_schemes': 'Show me government schemes',
            'request_mentor': 'I want to talk to a mentor',
            'create_plan': 'I want to create a business plan',
            'continue': 'Let me continue',
            'food': 'I am interested in cooking and food',
            'tailoring': 'I am interested in sewing and tailoring',
            'dairy': 'I am interested in dairy and livestock',
            'agriculture': 'I am interested in farming',
            'beauty': 'I am interested in beauty services',
            'handicraft': 'I am interested in handicrafts',
            'education': 'I am interested in teaching',
            'retail': 'I am interested in retail shop'
        }
        
        # Handle interest buttons (value is 'food', 'tailoring', etc.)
        if value in ['food', 'tailoring', 'dairy', 'agriculture', 'beauty', 'handicraft', 'education', 'retail']:
            # Map button values to readable text
            interest_map = {
                'food': 'Cooking & Food',
                'tailoring': 'Sewing & Tailoring',
                'dairy': 'Dairy & Livestock',
                'agriculture': 'Farming & Agriculture',
                'beauty': 'Beauty Services',
                'handicraft': 'Handicrafts & Art',
                'education': 'Teaching & Education',
                'retail': 'Retail & Shop'
            }
            
            readable_name = interest_map.get(value, value)
            if session_id in user_sessions:
                user_sessions[session_id]['context']['interests'] = readable_name
                user_sessions[session_id]['context']['categories'] = [value]
            
            # Directly call handle_idea_request to show budget options
            user_session = user_sessions[session_id]
            response = handle_idea_request(readable_name, user_session)
            
            # Save to history
            user_session['history'].append({
                'message': readable_name,
                'response': response.get('reply', ''),
                'intent': 'provide_interest',
                'timestamp': datetime.now().isoformat()
            })
            
            # Include context in response for frontend sync
            context = user_session['context']
            response['context'] = {
                'name': context.get('name'),
                'location': context.get('location') or context.get('village'),
                'interests': context.get('interests') or context.get('categories'),
                'budget': context.get('budget'),
                'has_ideas': bool(context.get('generated_ideas')),
                'has_plan': bool(context.get('generated_plan'))
            }
            
            return jsonify(response)
        
        # Handle budget buttons
        elif value.startswith('budget_'):
            budget_amount = int(value.replace('budget_', ''))
            if session_id in user_sessions:
                user_sessions[session_id]['context']['budget'] = budget_amount
            message = f"Under ₹{budget_amount}"
        else:
            message = message_map.get(value, value)
        
        # Add user message to history BEFORE processing
        if session_id in user_sessions:
            user_sessions[session_id]['history'].append({
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
        
        # Call chat function directly with data
        if session_id not in user_sessions:
            user_sessions[session_id] = {
                'user_id': None,
                'current_step': 'greeting',
                'context': {},
                'history': []
            }
        
        user_session = user_sessions[session_id]
        
        # For button clicks, DON'T extract entities from the message text
        # The context is already updated above (interests, budget, etc.)
        # Only detect intent for routing
        intent = detect_intent(message)
        
        # DEBUG: Print button state
        print(f"🔘 BUTTON - Value: '{value}', Message: '{message}'")
        print(f"🔘 BUTTON - Intent: {intent}")
        print(f"🔘 BUTTON - Context: name={user_session['context'].get('name')}, location={user_session['context'].get('location')}, village={user_session['context'].get('village')}, interests={user_session['context'].get('interests')}")
        
        # Smart state-based routing (same as chat endpoint)
        context = user_session['context']
        
        # Priority 1: Handle ongoing conversation flow
        if context.get('name') and not context.get('village') and not context.get('location'):
            # We have name but not location - treat specific button clicks as NOT location
            if value in ['show_ideas', 'find_resources', 'show_schemes', 'request_mentor']:
                # User clicked action button before giving location - redirect to get location
                response = {
                    "reply": f"First, please tell me which city or village you're from, {context['name']}? This will help me give you better suggestions.",
                    "type": "text_input"
                }
            elif intent == 'general' and len(message.strip()) > 0:
                response = handle_user_info(message, user_session, 'provide_location')
            else:
                response = handle_user_info(message, user_session, intent)
        
        elif context.get('name') and (context.get('village') or context.get('location')) and not context.get('interests'):
            # We have name and location but not interests
            if intent == 'provide_interest' or value.startswith('interest_'):
                # Handle interest selection - this should trigger idea request after setting interest
                response = handle_idea_request(message, user_session)
            elif intent == 'greeting':
                response = handle_greeting(message, user_session)
            elif intent == 'ask_for_ideas':
                response = handle_idea_request(message, user_session)
            elif intent == 'ask_resources':
                response = handle_resource_request(message, user_session)
            elif intent == 'ask_schemes':
                response = handle_scheme_request(message, user_session)
            else:
                # Default to asking for interests if not clear
                response = handle_idea_request(message, user_session)
        
        # Priority 2: Route based on explicit intent
        elif intent == 'greeting':
            response = handle_greeting(message, user_session)
        elif intent == 'ask_for_ideas' or value == 'show_ideas':
            response = handle_idea_request(message, user_session)
        elif intent == 'ask_resources' or value == 'find_resources':
            response = handle_resource_request(message, user_session)
        elif intent == 'ask_schemes' or value == 'show_schemes':
            response = handle_scheme_request(message, user_session)
        elif intent == 'ask_plan' or value == 'create_plan':
            response = handle_plan_request(message, user_session)
        elif intent == 'ask_mentor' or value == 'request_mentor':
            response = handle_mentor_request(message, user_session)
        elif intent in ['provide_name', 'provide_location', 'provide_interest', 'provide_budget']:
            response = handle_user_info(message, user_session, intent)
        else:
            response = handle_general_query(message, user_session)
        
        # Save response to history (important for context!)
        user_session['history'].append({
            'message': message,
            'response': response.get('reply', ''),
            'intent': intent,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save to database if user exists
        if user_session.get('user_id'):
            chat_record = ChatHistory(
                user_id=user_session['user_id'],
                message=message,
                response=response.get('reply', ''),
                intent=intent
            )
            db.session.add(chat_record)
            db.session.commit()
        
        # ALWAYS include current context in response for frontend sync
        response['context'] = {
            'name': context.get('name'),
            'location': context.get('location') or context.get('village'),
            'interests': context.get('interests') or context.get('categories'),
            'budget': context.get('budget'),
            'has_ideas': bool(context.get('generated_ideas')),
            'has_plan': bool(context.get('generated_plan'))
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/location/detect', methods=['POST'])
def detect_location():
    """Detect user's location from browser geolocation or IP"""
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        
        # Try to get location from request
        lat = data.get('latitude')
        lon = data.get('longitude')
        
        if lat and lon:
            # Reverse geocode to get city name
            from utils.location_service import get_location_details
            try:
                url = f"https://nominatim.openstreetmap.org/reverse"
                params = {
                    'lat': lat,
                    'lon': lon,
                    'format': 'json',
                    'addressdetails': 1
                }
                headers = {'User-Agent': 'StartupSathi/1.0'}
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    address = result.get('address', {})
                    
                    location_data = {
                        'city': address.get('city') or address.get('town') or address.get('village') or address.get('county'),
                        'state': address.get('state'),
                        'district': address.get('state_district'),
                        'country': address.get('country'),
                        'lat': lat,
                        'lon': lon
                    }
                    
                    # Store in session
                    if session_id in user_sessions:
                        user_sessions[session_id]['context']['location'] = location_data['city']
                        user_sessions[session_id]['context']['village'] = location_data['city']
                        user_sessions[session_id]['context']['location_data'] = location_data
                    
                    return jsonify({
                        'success': True,
                        'location': location_data
                    })
            except Exception as e:
                print(f"Reverse geocoding error: {e}")
        
        # Fallback to IP-based location
        from utils.location_service import get_user_location_from_ip
        location = get_user_location_from_ip()
        
        if location and session_id in user_sessions:
            user_sessions[session_id]['context']['location'] = location['city']
            user_sessions[session_id]['context']['village'] = location['city']
            user_sessions[session_id]['context']['location_data'] = location
        
        return jsonify({
            'success': True,
            'location': location,
            'method': 'ip'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/location/nearby', methods=['POST'])
def get_nearby_resources():
    """Get nearby resources based on location and business type"""
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        business_type = data.get('business_type', 'shop')
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        context = user_sessions[session_id]['context']
        location_data = context.get('location_data', {})
        
        if not location_data.get('lat') or not location_data.get('lon'):
            return jsonify({'error': 'Location not available'}), 400
        
        from utils.location_service import find_nearby_businesses
        nearby = find_nearby_businesses(
            location_data['lat'],
            location_data['lon'],
            business_type,
            radius_km=15
        )
        
        return jsonify({
            'success': True,
            'resources': nearby,
            'count': len(nearby)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Admin endpoints removed - everything is now dynamic

if __name__ == '__main__':
    with app.app_context():
        # Create tables for User and ChatHistory only
        db.create_all()
    
    print("🚀 Startup Sathi is running!")
    print("📱 Open http://localhost:5000 in your browser")
    print("✨ All responses are AI-generated dynamically!")
    app.run(debug=True, host='0.0.0.0', port=5000)

