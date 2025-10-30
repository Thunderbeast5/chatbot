# 🚀 Startup Sathi - AI-Powered Entrepreneurship Assistant

Complete chatbot for rural women entrepreneurs in India with AI-powered business guidance.

A comprehensive, AI-powered chatbot designed to help rural women entrepreneurs discover business ideas, create startup plans, find local resources, learn about government schemes, and connect with mentors.

## ✨ Features

### Core Functionality
- 🔍 **Business Idea Discovery**: Personalized business suggestions based on interests, location, and budget
- 📋 **Startup Plan Generation**: Detailed, actionable startup plans using Groq LLM (Llama 3.1)
- 📍 **Resource Finder**: Locate nearby suppliers, markets, banks, government offices using OpenStreetMap
- 💰 **Government Schemes**: Comprehensive database of schemes with eligibility and application process
- 👥 **Mentor Connection**: Request mentorship and guidance
- 💬 **Conversational AI**: Natural language understanding with intent detection
- 🗺️ **Interactive Maps**: Visual display of nearby resources using Leaflet.js
- 📊 **Smart Search**: Semantic search using sentence transformers for accurate idea matching

### Technology Stack
- **Backend**: Python 3.10+, Flask
- **Database**: SQLite (easily upgradeable to PostgreSQL)
- **NLP**: 
  - Groq API (Llama 3.1 70B) for intelligent responses
  - Sentence Transformers for semantic search
  - Custom intent detection
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Maps**: Leaflet.js + OpenStreetMap
- **Geocoding**: Nominatim API
- **Resources**: Overpass API

## 📁 Project Structure

```
Chatbot1/
├── app.py                      # Main Flask application
├── models.py                   # Database models (SQLAlchemy)
├── requirements.txt            # Python dependencies
├── nlp/
│   ├── __init__.py
│   ├── intent.py              # Intent detection & entity extraction
│   └── embed.py               # Semantic search engine
├── utils/
│   ├── geocoding.py           # Location & resource finding
│   └── llm.py                 # Groq LLM integration
├── data/
│   ├── seed.py                # Database seeding
│   └── idea_embeddings.pkl    # Cached embeddings (auto-generated)
├── static/
│   ├── css/
│   │   └── style.css          # Responsive styling
│   └── js/
│       └── app.js             # Frontend logic
├── templates/
│   └── index.html             # Main chat interface
└── startup_sathi.db           # SQLite database (auto-generated)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Internet connection (for APIs)

### Installation

1. **Clone or navigate to the project directory**
```powershell
cd C:\Users\tz8e\OneDrive\Desktop\Chatbot\Chatbot1
```

2. **Create a virtual environment** (recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. **Install dependencies**
```powershell
pip install -r requirements.txt
```

4. **Download spaCy model** (optional, for enhanced NLP)
```powershell
python -m spacy download en_core_web_sm
```

5. **Run the application**
```powershell
python app.py
```

6. **Open your browser**
Navigate to: `http://localhost:5000`

## 🎯 How It Works

### 1. User Onboarding Flow
- Bot greets user and asks for name
- Collects location (village/city)
- Understands interests through natural conversation or button selections
- Asks about budget constraints

### 2. Business Idea Discovery
- Uses semantic search to match user profile with 20+ pre-loaded business ideas
- Ideas include: Pickle making, Tailoring, Dairy, Snacks, Goat farming, Beauty parlour, Handicrafts, etc.
- Filters by budget and category
- Displays top 5 relevant suggestions

### 3. Startup Plan Generation
- User selects an idea
- Groq LLM generates comprehensive plan:
  - Overview and skills required
  - Investment breakdown
  - 12-month timeline
  - Resources needed
  - Revenue estimates
  - Risk mitigation
  - Next immediate steps

### 4. Resource Finding
- Geocodes user's location using Nominatim
- Queries Overpass API for nearby:
  - Suppliers (hardware, agricultural)
  - Markets
  - Banks
  - Government offices
  - Training centers
- Displays on interactive map

### 5. Government Schemes
- 10+ pre-loaded schemes including:
  - Mudra Loan
  - Stand-Up India
  - PMEGP
  - DDU-GKY
  - Mahila Udyam Nidhi
- Shows eligibility, benefits, and application links

### 6. Mentor Connection
- Collects user details
- Creates mentor request in database
- Admin/mentor dashboard ready (can be extended)

## 🔧 Configuration

### Groq API Key
Already configured in `utils/llm.py`:
```python
client = Groq(api_key="***REDACTED***")
```

### Database
Default: SQLite (`startup_sathi.db`)
To use PostgreSQL:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/dbname'
```

### Port Configuration
Change port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5000)  # Change port here
```

## 📊 Database Schema

### Tables
- **users**: User profiles (name, phone, location, interests)
- **ideas**: Business ideas catalog (title, description, investment, skills)
- **plans**: Generated startup plans
- **schemes**: Government schemes database
- **resources**: Local resources
- **chat_history**: Conversation logs
- **mentor_requests**: Mentorship requests

## 🎨 Features in Detail

### Intent Detection
Recognizes intents like:
- `greeting`, `ask_for_ideas`, `ask_resources`, `ask_schemes`
- `ask_plan`, `ask_mentor`, `provide_name`, `provide_location`
- `provide_interest`, `provide_budget`

### Entity Extraction
Extracts:
- Names
- Locations (villages/cities)
- Budget amounts (with units: thousands, lakhs)
- Phone numbers

### Semantic Search
- Uses `all-MiniLM-L6-v2` model (lightweight, fast)
- Embeds idea descriptions
- Finds best matches based on user query
- Supports filtering by category and budget

### Groq LLM Integration
- Model: `llama-3.1-70b-versatile`
- Generates human-like, contextual responses
- Creates detailed startup plans
- Answers follow-up questions
- Maintains conversation context

## 🌐 API Endpoints

### Chat
```
POST /api/chat
Body: { "message": "user message", "session_id": "unique_id" }
Response: { "reply": "bot response", "type": "text", "buttons": [...] }
```

### Select Idea
```
POST /api/select_idea
Body: { "idea_id": 1, "session_id": "unique_id" }
```

### Button Click
```
POST /api/button_click
Body: { "value": "show_ideas", "session_id": "unique_id" }
```

### Admin - Manage Schemes
```
GET /api/admin/schemes
POST /api/admin/schemes
Body: { "title": "...", "region": "...", ... }
```

## 📱 User Interface

### Chat Interface
- Clean, modern design with gradient theme
- Message bubbles (user vs bot)
- Button-based interactions for easy navigation
- Loading animations
- Responsive layout

### Information Panel
- Dynamic content display
- Business ideas grid
- Government schemes list
- Resources with map integration
- Detailed startup plans

### Interactive Elements
- Clickable business idea cards
- Government scheme cards with "Apply Now" links
- Map view with location markers
- Collapsible sections

## 🎓 Usage Examples

### Example Conversation 1: Discovery
```
User: Hello
Bot: Welcome! What's your name?
User: Priya
Bot: Nice to meet you, Priya! Which village are you from?
User: Bhopal
Bot: Great! What are you interested in?
User: I like cooking
Bot: [Shows food-related business ideas]
User: [Selects "Pickle Making"]
Bot: [Generates detailed startup plan]
```

### Example Conversation 2: Resources
```
User: Find suppliers near me
Bot: Please tell me your village name.
User: Pune
Bot: [Shows nearby hardware shops, markets, government offices]
[Displays interactive map]
```

### Example Conversation 3: Schemes
```
User: What government loans are available?
Bot: [Lists relevant schemes]
- Mudra Loan: Up to ₹10 lakh
- Stand-Up India: ₹10 lakh - ₹1 crore
- [Apply Now links]
```

## 🔐 Privacy & Security

- Minimal data collection
- Session-based user tracking
- No external data sharing
- Local database storage
- HTTPS recommended for production

## 🚀 Deployment

### Local Development
```powershell
python app.py
```

### Production (Example with Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Hosting Options
- **Free**: Render, Fly.io, PythonAnywhere
- **Paid**: AWS, Google Cloud, Azure, DigitalOcean

## 🛠️ Extending the Chatbot

### Add More Business Ideas
Edit `data/seed.py`:
```python
{
    "title": "Your New Idea",
    "description": "Description",
    "categories": "category1,category2",
    "required_investment_min": 5000,
    "required_investment_max": 25000,
    "tags": "tag1, tag2",
    "skills_required": "skill1, skill2"
}
```

### Add Government Schemes
Edit `data/seed.py`:
```python
{
    "title": "Scheme Name",
    "region": "All India",
    "eligibility": "Who can apply",
    "benefit": "What you get",
    "apply_link": "https://...",
    "documents": "Required docs",
    "category": "finance"
}
```

### Add Voice Support
Integrate Web Speech API in `app.js`:
```javascript
const recognition = new webkitSpeechRecognition();
recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    sendMessage(transcript);
};
```

### Add Multilingual Support
- Update prompts in `app.py`
- Use multilingual sentence transformer
- Translate UI text

## 📈 Future Enhancements

- [ ] Voice input/output
- [ ] Multilingual support (Hindi, regional languages)
- [ ] Mobile app (React Native)
- [ ] WhatsApp integration
- [ ] SMS notifications
- [ ] Payment gateway for schemes
- [ ] Video tutorials
- [ ] Community forum
- [ ] Progress tracking dashboard
- [ ] Analytics for mentors/admins

## 🐛 Troubleshooting

### Issue: Module not found
```powershell
pip install -r requirements.txt
```

### Issue: Database error
Delete `startup_sathi.db` and restart:
```powershell
rm startup_sathi.db
python app.py
```

### Issue: Groq API error
Check internet connection and API key validity.

### Issue: Map not loading
Check browser console for errors. Ensure Leaflet.js CDN is accessible.

## 📝 License

This project is open-source and available for educational and non-commercial use.

## 🤝 Contributing

Contributions welcome! Areas to improve:
- Add more business ideas
- Update government schemes
- Improve NLP accuracy
- Enhance UI/UX
- Add tests

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Review code comments
3. Test with sample data

## 🎉 Credits

- **Groq**: LLM API
- **Sentence Transformers**: Semantic search
- **OpenStreetMap**: Maps and geocoding
- **Leaflet.js**: Interactive maps
- **Flask**: Web framework

---

**Built with ❤️ for rural women entrepreneurs**

**Status**: ✅ Complete & Working
**Version**: 1.0.0
**Last Updated**: 2025
