import os
import re
import json
import logging
import urllib.parse
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Gemini API
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

gemini_model = None
multimodal_model = None

try:
    import google.generativeai as genai
    if API_KEY and API_KEY.strip() and API_KEY != "your_gemini_api_key_here":
        genai.configure(api_key=API_KEY.strip())
        # Try available fast models
        for model_candidate in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
            try:
                gemini_model = genai.GenerativeModel(model_candidate)
                multimodal_model = gemini_model
                logger.info(f"Initialized Gemini model: {model_candidate}")
                break
            except Exception as e:
                logger.warning(f"Could not load {model_candidate}: {e}")
except Exception as e:
    logger.warning(f"Gemini configuration notice: {e}")


def extract_json_from_response(text: str) -> dict:
    """
    Safely extract JSON object from Gemini markdown or raw text output.
    """
    if not text:
        return {}

    cleaned = text.strip()

    # Pattern 1: Look for ```json ... ``` code blocks
    json_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if json_block:
        candidate = json_block.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Pattern 2: Find first '{' and last '}'
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = cleaned[start_idx : end_idx + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Try to fix trailing commas
            fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                return json.loads(fixed)
            except Exception:
                pass

    # Pattern 3: Direct parse
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Failed to parse JSON from AI response: {e}")
        return {}


def build_shopping_links(category: str, search_terms: str) -> dict:
    """
    Build shopping deep links for Indian e-commerce & service platforms
    using urllib.parse.quote_plus.
    """
    q = urllib.parse.quote_plus(search_terms.strip() if search_terms else category)
    links = {}

    cat = (category or "").lower()

    # Home items
    if any(k in cat for k in ["light", "fan", "furniture", "table", "decor", "home", "living", "bedroom", "kitchen"]):
        links["amazon"] = f"https://www.amazon.in/s?k={q}"
        links["flipkart"] = f"https://www.flipkart.com/search?q={q}"
        links["ikea"] = f"https://www.ikea.com/in/en/search/?q={q}"
        links["myntra"] = f"https://www.myntra.com/search?q={q}"
        links["ajio"] = f"https://www.ajio.com/search/?text={q}"

    # Venue items
    elif "venue" in cat or "hall" in cat or "resort" in cat or "hotel" in cat:
        links["google"] = f"https://www.google.com/search?q={q}"
        links["booking"] = f"https://www.booking.com/search.html?ss={q}"
        links["makemytrip"] = f"https://www.makemytrip.com/hotels/hotel-listing/?searchText={q}"
        links["oyorooms"] = f"https://www.oyorooms.com/search/?location={q}"
        links["nobroker"] = f"https://www.nobroker.in/property/search/searchTerm={q}"

    # Catering / Food
    elif any(k in cat for k in ["cater", "food", "dining", "meal", "cake", "beverage", "snack"]):
        links["swiggy"] = f"https://www.swiggy.com/search?query={q}"
        links["zomato"] = f"https://www.zomato.com/search?q={q}"
        links["bigbasket"] = f"https://www.bigbasket.com/ps/?q={q}"
        links["amazon"] = f"https://www.amazon.in/s?k={q}"
        links["flipkart"] = f"https://www.flipkart.com/search?q={q}"

    # Entertainment
    elif any(k in cat for k in ["entertainment", "music", "dj", "game", "show"]):
        links["bookmyshow"] = f"https://in.bookmyshow.com/search?q={q}"
        links["amazon"] = f"https://www.amazon.in/s?k={q}"
        links["flipkart"] = f"https://www.flipkart.com/search?q={q}"

    # Jewelry
    elif any(k in cat for k in ["jewelry", "jewel", "necklace", "ring", "bracelet", "earring", "watch"]):
        links["amazon"] = f"https://www.amazon.in/s?k={q}"
        links["flipkart"] = f"https://www.flipkart.com/search?q={q}"
        links["bluestone"] = f"https://www.bluestone.com/search.html?query={q}"
        links["tanishq"] = f"https://www.tanishq.co.in/search?q={q}"
        links["caratlane"] = f"https://www.caratlane.com/search?q={q}"
        links["melorra"] = f"https://www.melorra.com/search?q={q}"
        links["meesho"] = f"https://www.meesho.com/search?q={q}"

    # General / Decoration
    else:
        links["amazon"] = f"https://www.amazon.in/s?k={q}"
        links["flipkart"] = f"https://www.flipkart.com/search?q={q}"
        links["meesho"] = f"https://www.meesho.com/search?q={q}"
        links["myntra"] = f"https://www.myntra.com/search?q={q}"

    return links


def build_party_category_links(cat_name: str, search_terms: str) -> dict:
    """
    Party planner specific platform deep-links as outlined in project specification.
    """
    q = urllib.parse.quote_plus(search_terms.strip() if search_terms else cat_name)
    cat = (cat_name or "").lower()

    category_platforms = {
        "venue": ["google", "booking", "makemytrip", "oyorooms", "nobroker"],
        "catering": ["swiggy", "zomato", "bigbasket"],
        "food": ["swiggy", "zomato", "bigbasket", "amazon", "flipkart"],
        "drinks": ["swiggy", "zomato", "bigbasket", "amazon", "flipkart"],
        "decoration": ["amazon", "flipkart", "meesho", "myntra"],
        "entertainment": ["bookmyshow", "amazon", "flipkart"],
        "gifts": ["amazon", "flipkart", "myntra", "meesho"],
        "photography": ["google", "amazon", "flipkart"],
        "music": ["amazon", "flipkart", "bookmyshow"],
        "games": ["amazon", "flipkart"],
        "accessories": ["amazon", "flipkart", "myntra", "meesho"],
        "transportation": ["makemytrip", "google"],
        "return_gifts": ["amazon", "flipkart", "myntra", "meesho"],
        "contingency": ["amazon", "flipkart", "google"],
    }

    relevant_platforms = category_platforms.get(cat, ["amazon", "flipkart", "google"])

    url_map = {
        "amazon": f"https://www.amazon.in/s?k={q}",
        "flipkart": f"https://www.flipkart.com/search?q={q}",
        "bigbasket": f"https://www.bigbasket.com/ps/?q={q}",
        "swiggy": f"https://www.swiggy.com/search?query={q}",
        "zomato": f"https://www.zomato.com/search?q={q}",
        "bookmyshow": f"https://in.bookmyshow.com/search?q={q}",
        "myntra": f"https://www.myntra.com/search?q={q}",
        "meesho": f"https://www.meesho.com/search?q={q}",
        "google": f"https://www.google.com/search?q={q}",
        "booking": f"https://www.booking.com/search.html?ss={q}",
        "makemytrip": f"https://www.makemytrip.com/hotels/hotel-listing/?searchText={q}",
        "oyorooms": f"https://www.oyorooms.com/search/?location={q}",
        "nobroker": f"https://www.nobroker.in/property/search/searchTerm={q}",
    }

    links = {}
    for plat in relevant_platforms:
        if plat in url_map:
            links[plat] = url_map[plat]
    return links


# ==========================================
# 1. HOME INTERIOR PLANNER
# ==========================================
def get_home_recommendations(budget_input) -> dict:
    """
    Generate home interior recommendations within budget in INR for Indian market.
    """
    total_budget = float(budget_input.total_budget)
    num_lights = getattr(budget_input, "num_lights", 4)
    num_fans = getattr(budget_input, "num_fans", 2)
    num_furniture = getattr(budget_input, "num_furniture", 2)
    num_dining_tables = getattr(budget_input, "num_dining_tables", 1)

    has_living = getattr(budget_input, "has_living_room", True)
    has_kitchen = getattr(budget_input, "has_kitchen", True)
    has_bedroom = getattr(budget_input, "has_bedroom", True)
    additional_reqs = getattr(budget_input, "additional_requirements", "") or "None"

    rooms_list = []
    if has_living:
        rooms_list.append("Living room")
    if has_kitchen:
        rooms_list.append("Kitchen")
    if has_bedroom:
        rooms_list.append("Bedroom")
    rooms_text = ", ".join(rooms_list) if rooms_list else "General home spaces"

    prompt = f"""
I need interior design product recommendations for a home in India with a total budget of ₹{total_budget:.2f}.
Requirements:
- {num_lights} lights/lighting fixtures
- {num_fans} ceiling fans
- {num_furniture} furniture pieces
- {num_dining_tables} dining tables

Additional rooms to consider:
{'- Living room' if has_living else ''}
{'- Kitchen' if has_kitchen else ''}
{'- Bedroom' if has_bedroom else ''}

Additional requirements: {additional_reqs}

Please provide a detailed budget breakdown with product recommendations **available in India**.
Use **Indian brands and pricing**. Include **search terms** suitable for Indian shopping platforms.

Format your response as strictly valid JSON with the following structure:
{{
  "total_budget": {total_budget:.2f},
  "budget_breakdown": [
    {{
      "category": "lighting",
      "allocation": 0.0,
      "items": [
        {{
          "name": "LED Warm White Ceiling Downlight",
          "description": "Energy-efficient LED bulbs for warm ambient room lighting.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "Philips 12W LED ceiling downlight warm white"
        }}
      ]
    }},
    {{
      "category": "ceiling_fans",
      "allocation": 0.0,
      "items": [
        {{
          "name": "BLDC High Speed Ceiling Fan",
          "description": "5-star energy saving BLDC motor ceiling fan with remote control.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "Atomberg Crompton BLDC 1200mm ceiling fan"
        }}
      ]
    }},
    {{
      "category": "furniture",
      "allocation": 0.0,
      "items": [
        {{
          "name": "Ergonomic 3-Seater Fabric Sofa",
          "description": "Modern compact sofa suitable for living room with washable cushions.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "Wakefit modern 3 seater fabric sofa"
        }}
      ]
    }},
    {{
      "category": "dining_tables",
      "allocation": 0.0,
      "items": [
        {{
          "name": "Solid Wood 4-Seater Dining Set",
          "description": "Durable Sheesham wood compact dining table with 4 cushioned chairs.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "Solid wood 4 seater dining table set"
        }}
      ]
    }}
  ],
  "calculation_table": [
    {{
      "category": "Lighting",
      "items_count": 0,
      "total_cost": 0.0,
      "percentage_of_budget": 0.0
    }}
  ],
  "remaining_budget": 0.0,
  "additional_suggestions": [
    "Consider purchasing LED fixtures in multipacks for 20-30% additional savings.",
    "Look out for festive discounts and cashback offers on e-commerce platforms.",
    "Opt for multipurpose furniture with built-in storage to maximize living area utility."
  ]
}}
Ensure all costs stay strictly within total budget of ₹{total_budget:.2f}. Include search terms for each item to find on shopping websites like Flipkart, Amazon India, IKEA, Myntra, Ajio.
"""

    result = None
    if gemini_model:
        try:
            response = gemini_model.generate_content(prompt)
            result = extract_json_from_response(response.text)
        except Exception as e:
            logger.warning(f"Gemini home API call failed: {e}. Falling back to smart generator.")

    # High-quality dynamic fallback engine if AI is unavailable or parsed empty
    if not result or "budget_breakdown" not in result:
        result = _generate_fallback_home_plan(total_budget, num_lights, num_fans, num_furniture, num_dining_tables, rooms_text, additional_reqs)

    # Post-process: inject shopping links & format
    total_spent = 0.0
    calc_table = []

    for cat_data in result.get("budget_breakdown", []):
        cat_cost = 0.0
        cat_items_count = 0
        cat_name = cat_data.get("category", "").lower()

        for item in cat_data.get("items", []):
            item_price = float(item.get("estimated_price", 0.0))
            item_qty = int(item.get("quantity", 1))
            cat_cost += item_price * item_qty
            cat_items_count += item_qty

            search_terms = item.get("search_terms") or item.get("name", "")
            item["shopping_links"] = {
                "amazon": f"https://www.amazon.in/s?k={urllib.parse.quote_plus(search_terms)}",
                "flipkart": f"https://www.flipkart.com/search?q={urllib.parse.quote_plus(search_terms)}",
                "ikea": f"https://www.ikea.com/in/en/search/?q={urllib.parse.quote_plus(search_terms)}",
                "myntra": f"https://www.myntra.com/search?q={urllib.parse.quote_plus(search_terms)}",
                "ajio": f"https://www.ajio.com/search/?text={urllib.parse.quote_plus(search_terms)}",
            }

        cat_data["allocation"] = round(cat_cost, 2)
        total_spent += cat_cost

        pct = (cat_cost / total_budget * 100) if total_budget > 0 else 0
        calc_table.append({
            "category": cat_data.get("category", "General").replace("_", " ").title(),
            "items_count": cat_items_count,
            "total_cost": round(cat_cost, 2),
            "percentage_of_budget": round(pct, 1)
        })

    result["total_budget"] = round(total_budget, 2)
    result["total_spent"] = round(total_spent, 2)
    result["remaining_budget"] = max(0.0, round(total_budget - total_spent, 2))
    result["calculation_table"] = calc_table

    if not result.get("additional_suggestions"):
        result["additional_suggestions"] = [
            "Consider purchasing energy-efficient 5-star BLDC fans for long-term electricity bill savings.",
            "Look for modular furniture with under-seat storage to optimize room spaces.",
            "Compare prices across IKEA and Amazon India during seasonal sales for best discounts."
        ]

    return result


def _generate_fallback_home_plan(total_budget: float, lights: int, fans: int, furniture: int, dining: int, rooms: str, reqs: str) -> dict:
    """Intelligent fallback for Home Interior Planner based on budget proportions."""
    # Proportions: Lighting (15%), Fans (20%), Furniture (45%), Dining (15%), Buffer (5%)
    p_light = total_budget * 0.15
    p_fan = total_budget * 0.20
    p_furn = total_budget * 0.45
    p_dining = total_budget * 0.15

    light_unit = round(p_light / max(1, lights), 2)
    fan_unit = round(p_fan / max(1, fans), 2)
    furn_unit = round(p_furn / max(1, furniture), 2)
    dining_unit = round(p_dining / max(1, dining), 2)

    return {
        "total_budget": total_budget,
        "budget_breakdown": [
            {
                "category": "lighting",
                "allocation": round(p_light, 2),
                "items": [
                    {
                        "name": "Philips Cool Daylight LED Ceiling Fixture",
                        "description": "Energy-saving glare-free downlights ideal for rooms.",
                        "estimated_price": light_unit,
                        "quantity": lights,
                        "search_terms": "Philips 12W LED ceiling downlight warm white"
                    }
                ]
            },
            {
                "category": "ceiling_fans",
                "allocation": round(p_fan, 2),
                "items": [
                    {
                        "name": "Havells / Atomberg BLDC Ceiling Fan",
                        "description": "Silent high-speed 1200mm ceiling fan with energy star rating.",
                        "estimated_price": fan_unit,
                        "quantity": fans,
                        "search_terms": "Havells Atomberg BLDC 1200mm ceiling fan"
                    }
                ]
            },
            {
                "category": "furniture",
                "allocation": round(p_furn, 2),
                "items": [
                    {
                        "name": "Modern Minimalist Wooden Sofa / Lounge Set",
                        "description": f"Comfortable ergonomic seating suited for {rooms}.",
                        "estimated_price": furn_unit,
                        "quantity": furniture,
                        "search_terms": "Wakefit modern compact wooden sofa set"
                    }
                ]
            },
            {
                "category": "dining_tables",
                "allocation": round(p_dining, 2),
                "items": [
                    {
                        "name": "Compact Engineered Wood Dining Table",
                        "description": "Space-saving durable dining table set with modern finish.",
                        "estimated_price": dining_unit,
                        "quantity": dining,
                        "search_terms": "IKEA wooden 4 seater dining table"
                    }
                ]
            }
        ],
        "calculation_table": [],
        "remaining_budget": round(total_budget * 0.05, 2),
        "additional_suggestions": [
            f"Tailored for {rooms} with smart space optimization.",
            "Use warm lighting in the living area and bright white LED in study/kitchen areas.",
            "Check IKEA and Amazon India for bundle furniture offers."
        ]
    }


# ==========================================
# 2. PARTY BUDGET PLANNER
# ==========================================
def get_party_recommendations(budget_input) -> dict:
    """
    Generate event and party budget recommendations in INR.
    Proportions budget across venue, catering, decoration, entertainment, contingency.
    """
    total_budget = float(budget_input.total_budget)
    num_guests = getattr(budget_input, "num_guests", 15)
    party_type = getattr(budget_input, "party_type", "Birthday")
    venue_type = getattr(budget_input, "venue_type", "Home")

    needs_catering = getattr(budget_input, "needs_catering", True)
    needs_decoration = getattr(budget_input, "needs_decoration", True)
    needs_entertainment = getattr(budget_input, "needs_entertainment", True)
    additional_reqs = getattr(budget_input, "additional_requirements", "") or "None"

    prompt = f"""
I need party planning recommendations for India with a total budget of ₹{total_budget:.2f}.
Party details:
- Type: {party_type}
- Number of guests: {num_guests}
- Venue type: {venue_type}
- Catering needed: {"Yes" if needs_catering else "No"}
- Decoration needed: {"Yes" if needs_decoration else "No"}
- Entertainment needed: {"Yes" if needs_entertainment else "No"}
- Additional requirements: {additional_reqs}

Please provide a detailed budget breakdown with specific recommendations available in India using INR prices.
Use Indian brands, services, and realistic cost expectations.

Format your response strictly as JSON with the following structure:
{{
  "total_budget": {total_budget:.2f},
  "budget_breakdown": [
    {{
      "category": "venue",
      "allocation": 0.0,
      "items": [
        {{
          "name": "Venue Booking / Space Setup",
          "description": "Space arrangement for {party_type} event.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "{venue_type} party venue hall rental"
        }}
      ]
    }},
    {{
      "category": "catering",
      "allocation": 0.0,
      "items": [
        {{
          "name": "Buffet Party Catering",
          "description": "Starters, main course buffet, beverages, and dessert for {num_guests} guests.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "Party catering bulk food order"
        }}
      ]
    }},
    {{
      "category": "decoration",
      "allocation": 0.0,
      "items": [
        {{
          "name": "Theme Balloon Arch & Backdrop Setup",
          "description": "Vibrant decoration kit including LED lights, banners, and balloons.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "{party_type} party theme decoration kit"
        }}
      ]
    }},
    {{
      "category": "entertainment",
      "allocation": 0.0,
      "items": [
        {{
          "name": "Party Speaker & Game Setup",
          "description": "High bass Bluetooth party speaker, playlist, and fun party games.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "Party bluetooth speaker board games"
        }}
      ]
    }},
    {{
      "category": "contingency",
      "allocation": 0.0,
      "items": [
        {{
          "name": "Buffer / Emergency Fund",
          "description": "Reserved for last minute guest additions or disposable tableware.",
          "estimated_price": 0.0,
          "quantity": 1,
          "search_terms": "Disposable party plates cups napkins set"
        }}
      ]
    }}
  ],
  "venue_suggestions": [
    {{
      "name": "{venue_type} Setup",
      "type": "{venue_type}",
      "capacity": {num_guests},
      "estimated_cost": 0.0,
      "search_terms": "{venue_type} rental near me"
    }}
  ],
  "remaining_budget": 0.0,
  "additional_suggestions": [
    "Opt for buffet-style catering to minimize service costs and food wastage.",
    "Order decorative balloon packs and DIY lights online 3 days before the party.",
    "Create a collaborative Spotify party playlist for free high-energy entertainment."
  ]
}}
Ensure all costs are in INR and total does not exceed the given budget.
Provide search terms suitable for Indian websites such as BookMyShow, Swiggy, Flipkart, MakeMyTrip, OYO.
"""

    result = None
    if gemini_model:
        try:
            response = gemini_model.generate_content(prompt)
            result = extract_json_from_response(response.text)
        except Exception as e:
            logger.warning(f"Gemini party API call failed: {e}. Falling back to smart generator.")

    if not result or "budget_breakdown" not in result:
        result = _generate_fallback_party_plan(total_budget, num_guests, party_type, venue_type, needs_catering, needs_decoration, needs_entertainment, additional_reqs)

    # Post-processing calculation table and shopping links
    categories_calc = {}
    total_allocated = 0.0

    for category in result.get("budget_breakdown", []):
        cat_name = category.get("category", "misc").lower()
        items = category.get("items", [])
        cat_cost = 0.0
        cat_count = 0

        for item in items:
            item_price = float(item.get("estimated_price", 0.0))
            item_qty = int(item.get("quantity", 1))
            cost = item_price * item_qty
            cat_cost += cost
            cat_count += item_qty

            search_terms = item.get("search_terms", "") or item.get("name", "")
            item["shopping_links"] = build_party_category_links(cat_name, search_terms)

        category["allocation"] = round(cat_cost, 2)
        total_allocated += cat_cost

        pct = (cat_cost / total_budget * 100) if total_budget > 0 else 0
        categories_calc[cat_name] = {
            "category": cat_name.replace("_", " ").title(),
            "items_count": cat_count,
            "total_cost": round(cat_cost, 2),
            "percentage_of_budget": round(pct, 1)
        }

    # Venue suggestions links
    for venue in result.get("venue_suggestions", []):
        v_terms = venue.get("search_terms") or venue.get("name", "")
        q_v = urllib.parse.quote_plus(v_terms)
        venue["search_links"] = {
            "google": f"https://www.google.com/search?q={q_v}",
            "booking": f"https://www.booking.com/search.html?ss={q_v}",
            "makemytrip": f"https://www.makemytrip.com/hotels/hotel-listing/?searchText={q_v}",
            "oyorooms": f"https://www.oyorooms.com/search/?location={q_v}",
            "nobroker": f"https://www.nobroker.in/property/search?searchTerm={q_v}"
        }

    result["total_budget"] = round(total_budget, 2)
    result["total_allocated"] = round(total_allocated, 2)
    result["remaining_budget"] = max(0.0, round(total_budget - total_allocated, 2))
    result["calculation_table_inr"] = list(categories_calc.values())

    return result


def _generate_fallback_party_plan(total_budget: float, guests: int, ptype: str, vtype: str, catering: bool, decor: bool, entertainment: bool, reqs: str) -> dict:
    """Intelligent fallback for Party Planner."""
    active_cats = 1  # Contingency is always active
    if "home" not in vtype.lower():
        active_cats += 1
    if catering:
        active_cats += 1
    if decor:
        active_cats += 1
    if entertainment:
        active_cats += 1

    # Proportions
    v_ratio = 0.20 if "home" not in vtype.lower() else 0.05
    c_ratio = 0.50 if catering else 0.0
    d_ratio = 0.15 if decor else 0.0
    e_ratio = 0.15 if entertainment else 0.0
    rem_ratio = 1.0 - (v_ratio + c_ratio + d_ratio + e_ratio)
    contingency_ratio = max(0.05, rem_ratio)

    sum_r = v_ratio + c_ratio + d_ratio + e_ratio + contingency_ratio
    v_cost = round((v_ratio / sum_r) * total_budget, 2)
    c_cost = round((c_ratio / sum_r) * total_budget, 2)
    d_cost = round((d_ratio / sum_r) * total_budget, 2)
    e_cost = round((e_ratio / sum_r) * total_budget, 2)
    contingency_cost = round((contingency_ratio / sum_r) * total_budget, 2)

    breakdown = []

    # Venue
    breakdown.append({
        "category": "venue",
        "allocation": v_cost,
        "items": [
            {
                "name": f"{vtype} Arrangement & Seating",
                "description": f"Space booking and chairs arrangement for {guests} guests.",
                "estimated_price": v_cost,
                "quantity": 1,
                "search_terms": f"{vtype} party venue hall booking"
            }
        ]
    })

    # Catering
    if catering:
        per_head = round(c_cost / max(1, guests), 2)
        breakdown.append({
            "category": "catering",
            "allocation": c_cost,
            "items": [
                {
                    "name": f"{ptype} Buffet Platter & Beverages",
                    "description": f"Appetizers, main dishes, and cool drinks (₹{per_head}/head).",
                    "estimated_price": per_head,
                    "quantity": guests,
                    "search_terms": "Swiggy Zomato party food catering bulk platter"
                }
            ]
        })

    # Decoration
    if decor:
        breakdown.append({
            "category": "decoration",
            "allocation": d_cost,
            "items": [
                {
                    "name": f"{ptype} Celebration Decor & LED Lights Kit",
                    "description": "Photo backdrop, helium balloon arch, fairy string lights.",
                    "estimated_price": d_cost,
                    "quantity": 1,
                    "search_terms": f"{ptype} party theme decoration lights set"
                }
            ]
        })

    # Entertainment
    if entertainment:
        breakdown.append({
            "category": "entertainment",
            "allocation": e_cost,
            "items": [
                {
                    "name": "Party Sound System & Fun Group Activities",
                    "description": "High output speaker and interactive party games.",
                    "estimated_price": e_cost,
                    "quantity": 1,
                    "search_terms": "Party soundbar karaoke bluetooth speaker"
                }
            ]
        })

    # Contingency
    breakdown.append({
        "category": "contingency",
        "allocation": contingency_cost,
        "items": [
            {
                "name": "Emergency Reserve & Disposables",
                "description": "Reserve fund for last-minute snacks, paper plates, napkins.",
                "estimated_price": contingency_cost,
                "quantity": 1,
                "search_terms": "Eco-friendly disposable party plates cups"
            }
        ]
    })

    return {
        "total_budget": total_budget,
        "budget_breakdown": breakdown,
        "venue_suggestions": [
            {
                "name": f"{vtype} Celebration Hall",
                "type": vtype,
                "capacity": guests,
                "estimated_cost": v_cost,
                "search_terms": f"{vtype} party space booking"
            }
        ],
        "remaining_budget": 0.0,
        "additional_suggestions": [
            "Opt for combo meal platters on Swiggy or Zomato for best per-head rate.",
            "Set up DIY photo booth with simple fairy lights for Instagram-worthy snaps.",
            "Send digital e-invitations to track RSVPs and prevent over-ordering food."
        ]
    }


# ==========================================
# 3. MULTIMODAL JEWELRY PLANNER
# ==========================================
def get_jewelry_recommendations(budget_input, image_path: Optional[str] = None) -> dict:
    """
    Generate jewelry recommendations based on occasion, preferences, and optional outfit image in INR.
    """
    total_budget = float(budget_input.total_budget)
    occasion = getattr(budget_input, "occasion", "Party")
    preferences = getattr(budget_input, "preferences", "") or "Not specified"

    has_image = bool(image_path and os.path.exists(image_path))

    prompt = f"""
I need jewelry recommendations for India with a total budget of ₹{total_budget:.2f}.
Occasion: {occasion}
Preferences: {preferences}
Provide only India-relevant styles, availability, and price ranges in INR.
"""

    if has_image:
        prompt += """
An image of the outfit is uploaded. Analyze the outfit image thoroughly, considering its colors, design pattern, fabric, and occasion appropriateness.
Suggest complementary jewelry (bracelets, rings, watches, necklaces, earrings) that elevates the outfit without exceeding the budget.
"""
    else:
        prompt += """
Suggest complementary jewelry pieces (bracelets, rings, watches, necklaces, earrings) suitable for the occasion that stay strictly within the budget.
"""

    prompt += f"""
Format the output strictly as JSON with this exact schema:
{{
  "outfit_analysis": {{
    "colors": ["Primary Color", "Accent Color"],
    "style": "Contemporary / Ethnic / Minimalist",
    "formality": "Casual / Semi-formal / Formal / Festive"
  }},
  "total_budget": {total_budget:.2f},
  "jewelry_recommendations": [
    {{
      "item_type": "Necklace / Pendant",
      "description": "Delicate rose-gold or silver pendant chain complementing the neckline.",
      "style": "Minimalist Elegant",
      "estimated_price": 0.0,
      "search_terms": "rose gold floral pendant chain"
    }},
    {{
      "item_type": "Bracelet",
      "description": "Sleek adjustable charm bracelet that pairs seamlessly with the outfit.",
      "style": "Modern Chic",
      "estimated_price": 0.0,
      "search_terms": "silver adjustable charm bracelet"
    }},
    {{
      "item_type": "Ring",
      "description": "Solitaire or geometric stackable ring in matching metal tone.",
      "style": "Statement Accent",
      "estimated_price": 0.0,
      "search_terms": "zirconia minimalist statement ring"
    }},
    {{
      "item_type": "Watch",
      "description": "Classic metal mesh or slim leather strap watch matching the color palette.",
      "style": "Timeless",
      "estimated_price": 0.0,
      "search_terms": "rose gold slim dial women watch"
    }}
  ],
  "remaining_budget": 0.0,
  "styling_tips": [
    "Match metal tones across your watch and rings for a unified sophisticated aesthetic.",
    "If the outfit has intricate embroidery or bold prints, keep earrings and necklace subtle.",
    "Choose comfortable clasps and hypoallergenic metals for long party hours."
  ]
}}
Keep prices in INR and relevant to Indian brands (Tanishq, BlueStone, CaratLane, Melorra, etc.). Ensure sum of items does not exceed ₹{total_budget:.2f}.
"""

    result = None
    if gemini_model:
        try:
            if has_image:
                try:
                    img = Image.open(image_path)
                    response = multimodal_model.generate_content([prompt, img])
                    result = extract_json_from_response(response.text)
                except Exception as img_err:
                    logger.warning(f"Multimodal image call error: {img_err}. Trying text prompt.")
                    response = gemini_model.generate_content(prompt)
                    result = extract_json_from_response(response.text)
            else:
                response = gemini_model.generate_content(prompt)
                result = extract_json_from_response(response.text)
        except Exception as e:
            logger.warning(f"Gemini jewelry API call failed: {e}. Falling back to smart generator.")

    if not result or "jewelry_recommendations" not in result:
        result = _generate_fallback_jewelry_plan(total_budget, occasion, preferences, image_path)

    # Post-process shopping links for each jewelry item
    total_spent = 0.0
    for item in result.get("jewelry_recommendations", []):
        price = float(item.get("estimated_price", 0.0))
        total_spent += price
        search_terms = item.get("search_terms") or item.get("description", "jewelry")
        q = urllib.parse.quote_plus(search_terms)

        item["shopping_links"] = {
            "amazon": f"https://www.amazon.in/s?k={q}",
            "flipkart": f"https://www.flipkart.com/search?q={q}",
            "bluestone": f"https://www.bluestone.com/search.html?query={q}",
            "tanishq": f"https://www.tanishq.co.in/search?q={q}",
            "caratlane": f"https://www.caratlane.com/search?q={q}",
            "melorra": f"https://www.melorra.com/search?q={q}",
            "meesho": f"https://www.meesho.com/search?q={q}",
        }

    result["total_budget"] = round(total_budget, 2)
    result["total_spent"] = round(total_spent, 2)
    result["remaining_budget"] = max(0.0, round(total_budget - total_spent, 2))

    return result


def _generate_fallback_jewelry_plan(total_budget: float, occasion: str, preferences: str, image_path: Optional[str] = None) -> dict:
    """Intelligent fallback for Jewelry Planner with optional image color extraction."""
    # Analyze image colors if provided
    detected_colors = ["Royal Blue", "Gold Accent"]
    detected_style = "Elegant Occasion Wear"
    detected_formality = "Festive / Semi-Formal"

    if image_path and os.path.exists(image_path):
        try:
            with Image.open(image_path) as im:
                im_rgb = im.convert("RGB").resize((50, 50))
                colors = im_rgb.getcolors(maxcolors=2500)
                if colors:
                    dominant = sorted(colors, key=lambda x: x[0], reverse=True)[0][1]
                    # Map dominant RGB roughly to color name
                    r, g, b = dominant
                    if r > 150 and g < 100 and b < 100:
                        detected_colors = ["Crimson Red", "Warm Gold"]
                    elif b > 140 and r < 120:
                        detected_colors = ["Navy Blue", "Silver Tint"]
                    elif g > 130 and r < 120:
                        detected_colors = ["Emerald Green", "Antique Gold"]
                    elif r > 180 and g > 180 and b > 180:
                        detected_colors = ["Pearl White", "Platinum"]
                    elif r < 60 and g < 60 and b < 60:
                        detected_colors = ["Midnight Black", "Rose Gold"]
        except Exception:
            pass

    # Budget split: Necklace (35%), Bracelet (25%), Watch (25%), Ring (15%)
    p_neck = round(total_budget * 0.35, 2)
    p_brace = round(total_budget * 0.25, 2)
    p_watch = round(total_budget * 0.25, 2)
    p_ring = round(total_budget * 0.15, 2)

    return {
        "outfit_analysis": {
            "colors": detected_colors,
            "style": f"{occasion} {detected_style}",
            "formality": detected_formality
        },
        "total_budget": total_budget,
        "jewelry_recommendations": [
            {
                "item_type": "Necklace / Pendant",
                "description": f"Refined pendant necklace coordinated with {detected_colors[0]} accents and {occasion} mood.",
                "style": "Graceful Silhouette",
                "estimated_price": p_neck,
                "search_terms": f"CaratLane Tanishq {detected_colors[1].lower()} necklace pendant"
            },
            {
                "item_type": "Bracelet",
                "description": f"Contemporary adjustable link bracelet with subtle stone highlights.",
                "style": "Modern Sparkle",
                "estimated_price": p_brace,
                "search_terms": "BlueStone Melorra rose gold bracelet"
            },
            {
                "item_type": "Watch",
                "description": "Sleek designer dial watch featuring metallic strap that complements your jewelry.",
                "style": "Sophisticated Luxury",
                "estimated_price": p_watch,
                "search_terms": "Titan Fastrack women designer analog watch"
            },
            {
                "item_type": "Ring",
                "description": "Minimalist solitaire or dual-band stackable ring for everyday sparkle.",
                "style": "Contemporary Chic",
                "estimated_price": p_ring,
                "search_terms": "CaratLane silver zirconia stackable ring"
            }
        ],
        "remaining_budget": 0.0,
        "styling_tips": [
            f"Harmonize your jewelry with the {', '.join(detected_colors)} tones of your attire.",
            "Choose a statement piece (either necklace or earrings) as the focal visual highlight.",
            "Layer delicate rings and bracelets for an effortlessly modern look."
        ]
    }
