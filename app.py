import os
import re
import json
import uuid
import shutil
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    File,
    UploadFile,
    Form,
    Request,
    status,
    Response,
)
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

import gemini_utils

# Load environment configuration
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pocketsmart")

# Initialize FastAPI application
app = FastAPI(
    title="PocketSmart: AI Budget Planner",
    description="GenAI-powered cross-platform budget planning and recommendation system",
    version="1.0.0",
)

# Application Security and JWT Setup
SECRET_KEY = os.getenv("SECRET_KEY", "pocketsmart_super_secret_jwt_key_2026_secure")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Mount static files and Jinja2 templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def render_template(request: Request, name: str, context: Optional[Dict[str, Any]] = None, status_code: int = 200) -> HTMLResponse:
    """Helper to ensure compatibility with modern Starlette Jinja2Templates signatures."""
    ctx = dict(context or {})
    ctx["request"] = request
    return templates.TemplateResponse(request=request, name=name, context=ctx, status_code=status_code)


# ==========================================
# In-Memory & Persistent Storage
# ==========================================
USERS_FILE = os.path.join("data", "users.json")
RECOMMENDATIONS_FILE = os.path.join("data", "recommendations.json")

# Token Blacklist & Active Sessions
blacklisted_tokens = set()
active_sessions: Dict[str, Dict[str, Any]] = {}


def load_json(filepath: str, default: Any) -> Any:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(filepath: str, data: Any):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")


# Pre-seed a demo user if database is empty
users_db: Dict[str, Dict[str, Any]] = load_json(USERS_FILE, {})
if "demo" not in users_db:
    users_db["demo"] = {
        "username": "demo",
        "email": "demo@pocketsmart.ai",
        "full_name": "Demo User",
        "hashed_password": pwd_context.hash("demo123"),
    }
    save_json(USERS_FILE, users_db)

# Pre-seed user recommendations if empty
user_recommendations: Dict[str, List[Dict[str, Any]]] = load_json(RECOMMENDATIONS_FILE, {})
if "demo" not in user_recommendations:
    user_recommendations["demo"] = [
        {
            "id": "rec-demo-1",
            "timestamp": (datetime.now() - timedelta(hours=2)).strftime("%b %d, %Y, %I:%M %p"),
            "recommendation_type": "home",
            "input_summary": "₹50,000 for Living Room & Bedroom (4 Lights, 2 Fans, 2 Furniture)",
            "budget": 50000.0,
            "remaining": 2500.0,
            "full_result": {
                "total_budget": 50000.0,
                "remaining_budget": 2500.0,
                "total_spent": 47500.0,
                "budget_breakdown": [
                    {
                        "category": "lighting",
                        "allocation": 6000.0,
                        "items": [
                            {
                                "name": "Philips Smart Wi-Fi LED Downlights",
                                "description": "Color-changing ambient LED downlights with app control.",
                                "estimated_price": 1500.0,
                                "quantity": 4,
                                "search_terms": "Philips Smart LED ceiling light",
                                "shopping_links": {
                                    "amazon": "https://www.amazon.in/s?k=Philips+Smart+LED+ceiling+light",
                                    "flipkart": "https://www.flipkart.com/search?q=Philips+Smart+LED+ceiling+light",
                                    "ikea": "https://www.ikea.com/in/en/search/?q=Philips+Smart+LED+ceiling+light",
                                    "myntra": "https://www.myntra.com/search?q=Philips+Smart+LED+ceiling+light",
                                    "ajio": "https://www.ajio.com/search/?text=Philips+Smart+LED+ceiling+light",
                                }
                            }
                        ]
                    }
                ],
                "calculation_table": [
                    {"category": "Lighting", "items_count": 4, "total_cost": 6000.0, "percentage_of_budget": 12.0}
                ],
                "additional_suggestions": [
                    "Buy multipacks on Amazon India for smart bulbs to save up to 25%."
                ]
            }
        }
    ]
    save_json(RECOMMENDATIONS_FILE, user_recommendations)


# ==========================================
# Pydantic Request & Response Schemas
# ==========================================
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None


class RegisterUser(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str


class UserInDB(UserBase):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class HomeBudgetInput(BaseModel):
    total_budget: float
    num_lights: int = 4
    num_fans: int = 2
    num_furniture: int = 2
    num_dining_tables: int = 1
    has_living_room: bool = True
    has_kitchen: bool = True
    has_bedroom: bool = True
    additional_requirements: Optional[str] = None


class PartyBudgetInput(BaseModel):
    total_budget: float
    num_guests: int = 15
    party_type: str = "Birthday"
    venue_type: str = "Home"
    needs_catering: bool = True
    needs_decoration: bool = True
    needs_entertainment: bool = True
    additional_requirements: Optional[str] = None


class JewelryBudgetInput(BaseModel):
    total_budget: float
    occasion: str = "Party"
    preferences: Optional[str] = None


# ==========================================
# Authentication & Session Helpers
# ==========================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_token(request: Request) -> Optional[str]:
    """Retrieve token from Authorization header or 'access_token' cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token[7:].strip()
        return cookie_token.strip()
    return None


async def get_current_user(request: Request) -> Optional[UserInDB]:
    """Extract and validate user from token, return UserInDB or None."""
    token = await get_token(request)
    if not token or token in blacklisted_tokens:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username or username not in users_db:
            return None
        user_dict = users_db[username]
        if username in active_sessions:
            active_sessions[username]["last_activity"] = datetime.now(timezone.utc)
        return UserInDB(**user_dict)
    except JWTError:
        return None


async def get_current_active_user(request: Request) -> UserInDB:
    """Dependency that enforces authenticated user, redirects or raises 401."""
    user = await get_current_user(request)
    if not user:
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/login"}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def save_to_history(username: str, recommendation_type: str, input_data: dict, result: dict) -> str:
    """Save generated recommendation to user's history."""
    if username not in user_recommendations:
        user_recommendations[username] = []

    rec_id = f"rec-{uuid.uuid4().hex[:8]}"
    now_str = datetime.now().strftime("%b %d, %Y, %I:%M %p")

    total_budget = result.get("total_budget", input_data.get("total_budget", 0.0))
    remaining = result.get("remaining_budget", 0.0)

    if recommendation_type == "home":
        rooms = []
        if input_data.get("has_living_room"):
            rooms.append("Living")
        if input_data.get("has_bedroom"):
            rooms.append("Bed")
        if input_data.get("has_kitchen"):
            rooms.append("Kitchen")
        room_txt = ", ".join(rooms) if rooms else "All spaces"
        summary = f"₹{total_budget:,.0f} for {room_txt} ({input_data.get('num_lights', 0)} lights, {input_data.get('num_fans', 0)} fans)"
    elif recommendation_type == "party":
        summary = f"₹{total_budget:,.0f} for {input_data.get('party_type', 'Event')} ({input_data.get('num_guests', 0)} guests at {input_data.get('venue_type', 'Home')})"
    else:
        summary = f"₹{total_budget:,.0f} for {input_data.get('occasion', 'Special')} Occasion Jewelry"

    history_item = {
        "id": rec_id,
        "timestamp": now_str,
        "recommendation_type": recommendation_type,
        "input_summary": summary,
        "budget": total_budget,
        "remaining": remaining,
        "input_data": input_data,
        "full_result": result,
    }

    user_recommendations[username].insert(0, history_item)
    save_json(RECOMMENDATIONS_FILE, user_recommendations)
    return rec_id


# ==========================================
# Background Tasks: Session Cleanup
# ==========================================
@app.on_event("startup")
async def startup_event():
    async def cleanup_expired_sessions():
        while True:
            try:
                now = datetime.now(timezone.utc)
                expired = []
                for username, session in list(active_sessions.items()):
                    last_act = session.get("last_activity")
                    if last_act:
                        if (now - last_act).total_seconds() > (ACCESS_TOKEN_EXPIRE_MINUTES * 60):
                            expired.append(username)
                for uname in expired:
                    logger.info(f"Removing expired session for: {uname}")
                    active_sessions.pop(uname, None)
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
            await asyncio.sleep(300)

    asyncio.create_task(cleanup_expired_sessions())


# ==========================================
# Public & Authentication Routes
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page introducing PocketSmart AI features and testimonials."""
    user = await get_current_user(request)
    return render_template(
        request,
        "index.html",
        {"user": user, "page_title": "PocketSmart AI - Smart Budget & Recommendations"}
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page or redirect to dashboard if logged in."""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return render_template(request, "login.html", {"user": None, "error": None})


@app.post("/login")
async def login(request: Request):
    """Handle login authentication via Form or JSON."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            username = None
            password = None
    else:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

    if not username or not password:
        if "text/html" in request.headers.get("accept", ""):
            return render_template(
                request,
                "login.html",
                {"user": None, "error": "Username and password are required."},
                status_code=400,
            )
        raise HTTPException(status_code=400, detail="Username and password are required.")

    user_data = users_db.get(username)
    if not user_data or not verify_password(password, user_data["hashed_password"]):
        if "text/html" in request.headers.get("accept", ""):
            return render_template(
                request,
                "login.html",
                {"user": None, "error": "Invalid username or password."},
                status_code=401,
            )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)

    active_sessions[username] = {
        "username": username,
        "login_time": datetime.now(timezone.utc),
        "last_activity": datetime.now(timezone.utc),
        "token": token,
        "user_data": {},
    }

    if "text/html" in request.headers.get("accept", ""):
        redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        redirect.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
        )
        return redirect

    res = JSONResponse(content={"access_token": token, "token_type": "bearer", "username": username})
    res.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return res


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login endpoint."""
    user_data = users_db.get(form_data.username)
    if not user_data or not verify_password(form_data.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": form_data.username})
    active_sessions[form_data.username] = {
        "username": form_data.username,
        "login_time": datetime.now(timezone.utc),
        "last_activity": datetime.now(timezone.utc),
        "token": token,
        "user_data": {},
    }
    return {"access_token": token, "token_type": "bearer"}


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serve user registration page."""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return render_template(request, "register.html", {"user": None, "error": None})


@app.post("/register")
async def register(request: Request):
    """Create a new user account."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            email = body.get("email")
            password = body.get("password")
            confirm_password = body.get("confirm_password") or password
            full_name = body.get("full_name")
        except Exception:
            username = email = password = confirm_password = full_name = None
    else:
        form = await request.form()
        username = form.get("username")
        email = form.get("email")
        password = form.get("password")
        confirm_password = form.get("confirm_password") or password
        full_name = form.get("full_name")

    if not username or not email or not password:
        err = "All required fields must be filled."
        if "text/html" in request.headers.get("accept", ""):
            return render_template(request, "register.html", {"user": None, "error": err}, status_code=400)
        raise HTTPException(status_code=400, detail=err)

    if confirm_password and password != confirm_password:
        err = "Passwords do not match."
        if "text/html" in request.headers.get("accept", ""):
            return render_template(request, "register.html", {"user": None, "error": err}, status_code=400)
        raise HTTPException(status_code=400, detail=err)

    if username in users_db:
        err = f"Username '{username}' is already taken. Please choose another."
        if "text/html" in request.headers.get("accept", ""):
            return render_template(request, "register.html", {"user": None, "error": err}, status_code=400)
        raise HTTPException(status_code=400, detail=err)

    hashed_pw = get_password_hash(password)
    users_db[username] = {
        "username": username,
        "email": email,
        "full_name": full_name or username.title(),
        "hashed_password": hashed_pw,
    }
    save_json(USERS_FILE, users_db)

    token = create_access_token(data={"sub": username})
    active_sessions[username] = {
        "username": username,
        "login_time": datetime.now(timezone.utc),
        "last_activity": datetime.now(timezone.utc),
        "token": token,
        "user_data": {},
    }

    if "text/html" in request.headers.get("accept", ""):
        redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        redirect.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
        )
        return redirect

    res = JSONResponse(content={"message": "Registration successful", "username": username, "access_token": token})
    res.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return res


@app.api_route("/logout", methods=["GET", "POST"])
async def logout(request: Request):
    """Terminates session, blacklists token, and redirects to login."""
    token = await get_token(request)
    if token:
        blacklisted_tokens.add(token)
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if username and username in active_sessions:
                del active_sessions[username]
        except JWTError:
            pass

    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response


# ==========================================
# Session Metadata Endpoints
# ==========================================
@app.get("/session-info")
async def get_session_info(current_user: UserInDB = Depends(get_current_active_user)):
    """Retrieve metadata about the current user session."""
    if current_user.username in active_sessions:
        session = active_sessions[current_user.username]
        login_time = session.get("login_time")
        duration = int((datetime.now(timezone.utc) - login_time).total_seconds() // 60) if login_time else 0
        return {
            "username": session["username"],
            "login_time": session["login_time"].isoformat() if session.get("login_time") else None,
            "last_activity": session["last_activity"].isoformat() if session.get("last_activity") else None,
            "session_duration_minutes": duration,
            "user_data": session.get("user_data", {}),
        }
    raise HTTPException(status_code=404, detail="No active session found")


@app.post("/session-data")
async def update_session_data(data: Dict[str, Any], current_user: UserInDB = Depends(get_current_active_user)):
    """Update user session data for personalization."""
    if current_user.username in active_sessions:
        active_sessions[current_user.username]["user_data"].update(data)
        active_sessions[current_user.username]["last_activity"] = datetime.now(timezone.utc)
        return {"message": "Session data updated", "data": active_sessions[current_user.username]["user_data"]}
    raise HTTPException(status_code=404, detail="No active session found")


# ==========================================
# Application Pages (Protected)
# ==========================================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """User dashboard showing quick actions and recent activity."""
    recent_history = user_recommendations.get(current_user.username, [])[:5]
    return render_template(
        request,
        "dashboard.html",
        {
            "user": current_user,
            "recent_activity": recent_history,
            "page_title": "PocketSmart Dashboard",
        },
    )


@app.get("/home-planner", response_class=HTMLResponse)
async def home_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """Home interior budget planner interactive form & view."""
    return render_template(
        request,
        "home_planner.html",
        {"user": current_user, "page_title": "Home Interior Budget Planner"},
    )


@app.get("/party-planner", response_class=HTMLResponse)
async def party_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """Party & event budget planner interactive form & view."""
    return render_template(
        request,
        "party_planner.html",
        {"user": current_user, "page_title": "Party Budget Planner"},
    )


@app.get("/jewelry-planner", response_class=HTMLResponse)
async def jewelry_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """Multimodal jewelry recommendation planner interactive form & view."""
    return render_template(
        request,
        "jewelry_planner.html",
        {"user": current_user, "page_title": "Jewelry Budget Planner"},
    )


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    """User saved recommendation history page."""
    history_items = user_recommendations.get(current_user.username, [])
    return render_template(
        request,
        "history.html",
        {
            "user": current_user,
            "history": history_items,
            "page_title": "Your Recommendation History",
        },
    )


# ==========================================
# Planner Execution API Endpoints
# ==========================================

# 1. Home Interior Planner
@app.post("/home-budget")
@app.post("/generate-home")
async def plan_home_budget(
    budget_input: HomeBudgetInput,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Generate home interior budget recommendations."""
    try:
        if current_user.username in active_sessions:
            active_sessions[current_user.username]["user_data"]["last_home_budget"] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "budget": budget_input.total_budget,
                "requirements": {
                    "lights": budget_input.num_lights,
                    "fans": budget_input.num_fans,
                    "furniture": budget_input.num_furniture,
                    "dining_tables": budget_input.num_dining_tables,
                },
            }

        result = gemini_utils.get_home_recommendations(budget_input)

        rec_id = save_to_history(
            username=current_user.username,
            recommendation_type="home",
            input_data=budget_input.model_dump(),
            result=result,
        )
        result["recommendation_id"] = rec_id
        return result
    except Exception as e:
        logger.error(f"Error in plan_home_budget: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating home recommendations: {str(e)}")


# 2. Party Budget Planner
@app.post("/party-budget")
@app.post("/generate-party")
async def plan_party_budget(
    budget_input: PartyBudgetInput,
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Generate party planning and budget recommendations."""
    try:
        if current_user.username in active_sessions:
            active_sessions[current_user.username]["user_data"]["last_party_budget"] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "budget": budget_input.total_budget,
                "party_type": budget_input.party_type,
                "guests": budget_input.num_guests,
            }

        result = gemini_utils.get_party_recommendations(budget_input)

        rec_id = save_to_history(
            username=current_user.username,
            recommendation_type="party",
            input_data=budget_input.model_dump(),
            result=result,
        )
        result["recommendation_id"] = rec_id
        return result
    except Exception as e:
        logger.error(f"Error in plan_party_budget: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating party recommendations: {str(e)}")


# 3. Jewelry Planner (Multimodal: Form fields + Image Upload)
@app.post("/jewelry-budget")
@app.post("/generate-jewelry")
async def plan_jewelry_budget(
    request: Request,
    total_budget: float = Form(...),
    occasion: str = Form(...),
    preferences: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Generate multimodal jewelry recommendations with optional outfit image."""
    try:
        budget_input = JewelryBudgetInput(
            total_budget=total_budget,
            occasion=occasion,
            preferences=preferences,
        )

        image_path = None
        saved_filename = None

        if image and image.filename:
            ext = os.path.splitext(image.filename)[1].lower() or ".jpg"
            saved_filename = f"{uuid.uuid4().hex}{ext}"
            image_path = os.path.join("static", "uploads", saved_filename)
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

        if current_user.username in active_sessions:
            active_sessions[current_user.username]["user_data"]["last_jewelry_budget"] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "budget": total_budget,
                "occasion": occasion,
                "has_image": image_path is not None,
            }

        result = gemini_utils.get_jewelry_recommendations(budget_input, image_path)
        if saved_filename:
            result["uploaded_image_url"] = f"/static/uploads/{saved_filename}"

        input_data = budget_input.model_dump()
        if saved_filename:
            input_data["image"] = saved_filename

        rec_id = save_to_history(
            username=current_user.username,
            recommendation_type="jewelry",
            input_data=input_data,
            result=result,
        )
        result["recommendation_id"] = rec_id
        return result
    except Exception as e:
        logger.error(f"Error in plan_jewelry_budget: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating jewelry recommendations: {str(e)}")


# ==========================================
# History & Detail APIs
# ==========================================
@app.get("/recommendation-history")
async def get_recommendation_history(current_user: UserInDB = Depends(get_current_active_user)):
    """Retrieve full history list for current user."""
    history = user_recommendations.get(current_user.username, [])
    history_data = []
    for item in history:
        history_data.append({
            "id": item["id"],
            "timestamp": item["timestamp"],
            "type": item["recommendation_type"],
            "input": item["input_summary"],
            "budget": item.get("budget", 0),
            "remaining": item.get("remaining", 0),
            "summary": item.get("input_summary"),
        })
    return {"history": history_data}


@app.get("/recommendation-details/{recommendation_id}")
async def get_recommendation_details(
    recommendation_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Retrieve detailed data for a specific past recommendation."""
    user_items = user_recommendations.get(current_user.username, [])
    for item in user_items:
        if item["id"] == recommendation_id:
            return {
                "id": item["id"],
                "timestamp": item["timestamp"],
                "type": item["recommendation_type"],
                "input": item.get("input_summary"),
                "full_result": item.get("full_result", {}),
            }
    raise HTTPException(status_code=404, detail="Recommendation not found")


@app.delete("/recommendation-delete/{recommendation_id}")
async def delete_recommendation(
    recommendation_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Delete a recommendation entry from history."""
    if current_user.username in user_recommendations:
        user_recommendations[current_user.username] = [
            i for i in user_recommendations[current_user.username] if i["id"] != recommendation_id
        ]
        save_json(RECOMMENDATIONS_FILE, user_recommendations)
        return {"message": "Recommendation removed successfully"}
    raise HTTPException(status_code=404, detail="User history not found")


def usd_to_inr(amount_usd: float, exchange_rate: float = 83.0) -> float:
    """Convert USD amount to INR using the specified exchange rate."""
    return amount_usd * exchange_rate


if __name__ == "__main__":
    import uvicorn
    print("Starting PocketSmart: AI Budget Planner...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
