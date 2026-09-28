# PocketSmart AI: Smart Budget & Recommendation Assistant

**PocketSmart AI** is a GenAI-powered, cross-platform budget planning and recommendation system built with **FastAPI**, **Google Gemini 1.5 Flash / 2.0 Flash**, and an **HTML5/CSS3/JavaScript (Jinja2)** frontend.

The platform helps users enter a budget and specific requirements to receive structured, category-wise recommendations mapped with deep-links to e-commerce and service platforms (Amazon India, Flipkart, IKEA, Swiggy, Zomato, OYO, MakeMyTrip, Tanishq, CaratLane, and more).

---

## 🏗️ Architecture & Directory Structure

```
pocketsmart-ai/
│
├── static/
│   ├── uploads/            # Uploaded outfit images for multimodal analysis
│   └── styles.css          # Responsive dark-blue/light contrast UI styling
│
├── templates/
│   ├── index.html          # Landing page with hero, features & testimonials
│   ├── login.html          # Authentication: Login page
│   ├── register.html       # Authentication: Registration page
│   ├── dashboard.html      # User dashboard with quick links & activity timeline
│   ├── home_planner.html   # Home Interior Budget Planner
│   ├── party_planner.html  # Party & Event Budget Planner
│   ├── jewelry_planner.html# Multimodal Jewelry Recommendation Planner
│   └── history.html        # Saved recommendation history & interactive modal
│
├── data/                   # Persistent storage for users and recommendation history
│   ├── users.json
│   └── recommendations.json
│
├── gemini_utils.py         # Gemini AI integration, URL linking engine & fallback generator
├── app.py                  # Main FastAPI application entrypoint, routes, models & auth
├── requirements.txt        # Python dependencies
├── test_app.py             # Automated unit & integration test suite
└── .env                    # Environment variables (GOOGLE_API_KEY, SECRET_KEY)
```

---

## ⚡ Core Features & Planners

### 1. 🏠 Home Interior Budget Planner (`/home-planner` & `/home-budget`)
- **Inputs**: Total budget (₹ INR), lights/fixtures count, ceiling fans count, furniture pieces, dining tables, rooms selection (Living Room, Kitchen, Bedroom), and custom requirements.
- **AI Processing**: Gemini model allocates costs realistically across lighting, ceiling fans, furniture, and dining tables using Indian pricing.
- **Deep Shopping Links**: Dynamically maps search queries into **Amazon India**, **Flipkart**, **IKEA**, **Myntra**, and **Ajio**.
- **Calculation Table**: Complete summary breakdown of cost and percentage of budget per category.

### 2. 🎈 AI Party Budget Planner (`/party-planner` & `/party-budget`)
- **Inputs**: Total budget (₹ INR), guest count, event type (Birthday, Wedding, Anniversary, Corporate), venue type, party needs (Catering, Decoration, Entertainment), and additional notes.
- **AI Processing**: Proportions budget across venue booking, food & beverages catering, theme decorations, entertainment, and contingency buffer.
- **Platform Categorization**:
  - **Venue**: Google Maps, Booking.com, MakeMyTrip, OYO Rooms, NoBroker
  - **Catering / Food**: Swiggy, Zomato, BigBasket
  - **Decorations**: Amazon, Flipkart, Meesho, Myntra
  - **Entertainment**: BookMyShow, Amazon, Flipkart

### 3. 💎 Multimodal Jewelry Planner (`/jewelry-planner` & `/jewelry-budget`)
- **Inputs**: Total budget (₹ INR), occasion (Wedding, Birthday, Festive, Office), style preferences, and an **optional uploaded outfit image**.
- **Multimodal AI Analysis**: Analyzes outfit color palette, style, and formality using Google Gemini Vision, recommending complementary bracelets, rings, watches, and necklaces.
- **Indian Retailer Links**: Direct shopping links to **Tanishq**, **BlueStone**, **CaratLane**, **Melorra**, **Amazon**, **Flipkart**, and **Meesho**.

### 4. 🔐 Authentication, Session & History Management
- Secure password hashing using `passlib[bcrypt]`.
- JWT token authentication using `python-jose` with `access_token` cookies and Authorization Bearer header support.
- In-memory active session tracking with automatic background cleanup task every 5 minutes for sessions inactive > 30 minutes.
- Recommendation history persistence with interactive "View Full Details" breakdown modals and deletion support.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Pip

### 2. Configure Environment Variables
Open `.env` and set your Google Gemini API key:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
SECRET_KEY=pocketsmart_ai_super_secret_jwt_key_2026_secure
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
*(Note: If no API key is provided, the application automatically uses its intelligent fallback engine to supply realistic Indian market prices, calculations, and active deep shopping links).*

### 3. Run the Application
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

### 4. Pre-configured Demo Account
- **Username**: `demo`
- **Password**: `demo123`

Or register a new account on `/register`.

### 5. Run the Automated Tests
```bash
python test_app.py
```
All unit tests and API endpoints will be validated.
