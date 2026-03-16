"""
ShopVerse — AI-Powered Smart Shopping Platform
Flask Backend with MongoDB, Google Auth, Razorpay, Real-time Messaging
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import json, random, math, os, re, uuid, hashlib
from datetime import datetime, timedelta

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# ── MongoDB ───────────────────────────────────────────────────────────────────
from pymongo import MongoClient, DESCENDING
from bson import ObjectId

MONGO_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://praneetaphani_db_user:phani@shopverse.6ufzvam.mongodb.net/')
DB_NAME   = os.environ.get('DB_NAME', 'shopverse')

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()
    db = mongo_client[DB_NAME]
    print("✅ MongoDB connected:", DB_NAME)
    MONGO_OK = True
except Exception as e:
    print("⚠️  MongoDB unavailable, using in-memory:", e)
    db = None
    MONGO_OK = False

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'shopverse-secret-2024')
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID', 'rzp_live_SKKoU0dKi4yqx3')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'iZjR3mZES8i6kOKn7EGO0Gy2')
GOOGLE_CLIENT_ID    = os.environ.get('GOOGLE_CLIENT_ID', 'AIzaSyCNxbtSOKe8XCkSk6lPHSfs0wt6Jx2MWDI')

# In-memory fallbacks
_mem_users, _mem_orders, _mem_messages = {}, [], []
_mem_claimed_offers, _mem_store_visits = [], []
DISABLED_OFFERS = set()
DYNAMIC_STORES  = []

# ── STORE DATA ────────────────────────────────────────────────────────────────
DEMO_STORES = [
    {"id":"s1","name":"Campus Bakery","category":"bakery","lat":17.4401,"lng":78.4987,"rating":4.5,
     "mall":"College Campus","floor":"Ground Floor","shop_number":"G-01",
     "address":"College Campus, Building A","phone":"+91-98765-43210",
     "products":[
         {"id":"p1","name":"Chocolate Cake","price":200,"emoji":"🎂"},
         {"id":"p2","name":"Croissant","price":60,"emoji":"🥐"},
         {"id":"p3","name":"Garlic Bread","price":80,"emoji":"🍞"},
         {"id":"p4","name":"Cookies (6 pcs)","price":120,"emoji":"🍪"},
         {"id":"p5","name":"Donuts (2 pcs)","price":90,"emoji":"🍩"},
         {"id":"p6","name":"Sushi Roll","price":180,"emoji":"🍱"},
         {"id":"p7","name":"Tacos (2 pcs)","price":120,"emoji":"🌮"},
         {"id":"p8","name":"Pizza Slice","price":90,"emoji":"🍕"}
     ],"geofence_radius":200,"color":"#f59e0b"},
    {"id":"s2","name":"The Coffee Lab","category":"cafe","lat":17.4405,"lng":78.4992,"rating":4.3,
     "mall":"College Campus","floor":"Ground Floor","shop_number":"G-02",
     "address":"College Campus, Student Center","phone":"+91-98765-43211",
     "products":[
         {"id":"p10","name":"Espresso","price":80,"emoji":"☕"},
         {"id":"p11","name":"Cappuccino","price":120,"emoji":"☕"},
         {"id":"p12","name":"Cold Brew","price":150,"emoji":"🧊"},
         {"id":"p13","name":"Sandwich","price":180,"emoji":"🥪"},
         {"id":"p14","name":"Muffin","price":70,"emoji":"🧁"}
     ],"geofence_radius":200,"color":"#8b5cf6"},
    {"id":"s3","name":"QuickMart Superstore","category":"supermarket","lat":17.4395,"lng":78.4980,"rating":4.1,
     "mall":"College Campus","floor":"Ground Floor","shop_number":"G-03",
     "address":"College Campus, Main Street","phone":"+91-98765-43212",
     "products":[
         {"id":"p20","name":"Snack Combo Pack","price":250,"emoji":"🍿"},
         {"id":"p21","name":"Beverage Bundle","price":180,"emoji":"🥤"},
         {"id":"p22","name":"Fresh Juice","price":60,"emoji":"🍹"},
         {"id":"p23","name":"Energy Bar","price":45,"emoji":"🍫"},
         {"id":"p24","name":"Mixed Nuts","price":150,"emoji":"🥜"}
     ],"geofence_radius":200,"color":"#22c55e"},
    {"id":"s4","name":"Spice Garden Restaurant","category":"restaurant","lat":17.4408,"lng":78.4975,"rating":4.6,
     "mall":"College Campus","floor":"Food Court","shop_number":"FC-01",
     "address":"College Campus, Food Court","phone":"+91-98765-43213",
     "products":[
         {"id":"p30","name":"Biryani","price":180,"emoji":"🍛"},
         {"id":"p31","name":"Thali Combo","price":150,"emoji":"🍱"},
         {"id":"p32","name":"Burger","price":120,"emoji":"🍔"},
         {"id":"p33","name":"Pizza Slice","price":90,"emoji":"🍕"},
         {"id":"p34","name":"Lassi","price":60,"emoji":"🥛"},
         {"id":"p35","name":"Sushi Platter","price":320,"emoji":"🍣"},
         {"id":"p36","name":"Tacos","price":140,"emoji":"🌮"}
     ],"geofence_radius":200,"color":"#ef4444"},
    {"id":"s5","name":"Convenience Corner","category":"convenience_store","lat":17.4392,"lng":78.4995,"rating":3.9,
     "mall":"College Campus","floor":"Ground Floor","shop_number":"G-05",
     "address":"College Campus, Gate 2","phone":"+91-98765-43214",
     "products":[
         {"id":"p40","name":"Daily Essentials Kit","price":350,"emoji":"🛒"},
         {"id":"p41","name":"Stationery Pack","price":120,"emoji":"✏️"},
         {"id":"p42","name":"Mineral Water (1L)","price":25,"emoji":"💧"},
         {"id":"p43","name":"Chocolate Bar","price":40,"emoji":"🍫"},
         {"id":"p44","name":"Chips Pack","price":30,"emoji":"🥔"}
     ],"geofence_radius":200,"color":"#06b6d4"},
    {"id":"amb1","name":"Zara Fashion","category":"fashion","lat":17.4160,"lng":78.4350,"rating":4.4,
     "mall":"AMB Mall","floor":"1st Floor","shop_number":"1F-101",
     "address":"AMB Mall, Narsingi, Hyderabad","phone":"+91-40-6700-1001",
     "products":[
         {"id":"z1","name":"Men's Jeans","price":3990,"emoji":"👖"},
         {"id":"z2","name":"Women's Top","price":2490,"emoji":"👚"},
         {"id":"z3","name":"Summer Dress","price":4990,"emoji":"👗"},
         {"id":"z4","name":"Blazer","price":7990,"emoji":"🧥"},
         {"id":"z5","name":"Sneakers","price":5990,"emoji":"👟"}
     ],"geofence_radius":300,"color":"#000000"},
    {"id":"amb2","name":"H&M Clothing","category":"fashion","lat":17.4155,"lng":78.4345,"rating":4.2,
     "mall":"AMB Mall","floor":"Ground Floor","shop_number":"GF-201",
     "address":"AMB Mall, Narsingi, Hyderabad","phone":"+91-40-6700-1002",
     "products":[
         {"id":"hm1","name":"Cotton T-Shirt","price":799,"emoji":"👕"},
         {"id":"hm2","name":"Chinos","price":1999,"emoji":"👖"},
         {"id":"hm3","name":"Winter Jacket","price":4999,"emoji":"🧥"},
         {"id":"hm4","name":"Floral Skirt","price":1499,"emoji":"👗"},
         {"id":"hm5","name":"Accessories Set","price":599,"emoji":"💍"}
     ],"geofence_radius":300,"color":"#e50010"},
    {"id":"amb3","name":"Food Hall - AMB","category":"restaurant","lat":17.4158,"lng":78.4355,"rating":4.7,
     "mall":"AMB Mall","floor":"Food Court - 3rd Floor","shop_number":"3F-FC",
     "address":"AMB Mall Food Court, 3rd Floor","phone":"+91-40-6700-1003",
     "products":[
         {"id":"fh1","name":"Hyderabadi Biryani","price":250,"emoji":"🍛"},
         {"id":"fh2","name":"Pav Bhaji","price":120,"emoji":"🥘"},
         {"id":"fh3","name":"Sushi Platter","price":450,"emoji":"🍱"},
         {"id":"fh4","name":"Wood Fire Pizza","price":350,"emoji":"🍕"},
         {"id":"fh5","name":"Dessert Combo","price":180,"emoji":"🍨"},
         {"id":"fh6","name":"Cold Coffee","price":150,"emoji":"☕"}
     ],"geofence_radius":300,"color":"#f97316"},
    {"id":"amb4","name":"Sephora Beauty","category":"beauty","lat":17.4162,"lng":78.4342,"rating":4.5,
     "mall":"AMB Mall","floor":"Ground Floor","shop_number":"GF-105",
     "address":"AMB Mall, Ground Floor, Narsingi","phone":"+91-40-6700-1004",
     "products":[
         {"id":"sep1","name":"Foundation Set","price":2500,"emoji":"💄"},
         {"id":"sep2","name":"Skincare Kit","price":3200,"emoji":"🧴"},
         {"id":"sep3","name":"Perfume - 50ml","price":4500,"emoji":"🌸"},
         {"id":"sep4","name":"Lip Color Pack","price":1200,"emoji":"💋"},
         {"id":"sep5","name":"Eye Shadow Palette","price":1800,"emoji":"👁️"}
     ],"geofence_radius":300,"color":"#ec4899"},
    {"id":"amb5","name":"Cinemax AMB","category":"entertainment","lat":17.4153,"lng":78.4360,"rating":4.6,
     "mall":"AMB Mall","floor":"4th Floor","shop_number":"4F-CINEMA",
     "address":"AMB Mall, 4th Floor, Narsingi","phone":"+91-40-6700-1005",
     "products":[
         {"id":"cin1","name":"Movie Ticket (Standard)","price":200,"emoji":"🎬"},
         {"id":"cin2","name":"Movie Ticket (Gold)","price":350,"emoji":"🎭"},
         {"id":"cin3","name":"Popcorn Large","price":250,"emoji":"🍿"},
         {"id":"cin4","name":"Combo Meal","price":450,"emoji":"🥤"},
         {"id":"cin5","name":"IMAX Experience","price":500,"emoji":"🎥"}
     ],"geofence_radius":300,"color":"#7c3aed"},
    {"id":"amb6","name":"Apple Store AMB","category":"electronics","lat":17.4157,"lng":78.4340,"rating":4.8,
     "mall":"AMB Mall","floor":"1st Floor","shop_number":"1F-108",
     "address":"AMB Mall, 1st Floor, Narsingi","phone":"+91-40-6700-1006",
     "products":[
         {"id":"ap1","name":"iPhone 16 Pro","price":134900,"emoji":"📱"},
         {"id":"ap2","name":"MacBook Air M3","price":114900,"emoji":"💻"},
         {"id":"ap3","name":"AirPods Pro","price":24900,"emoji":"🎧"},
         {"id":"ap4","name":"iPad Pro 11\"","price":99900,"emoji":"📲"},
         {"id":"ap5","name":"Apple Watch Series 10","price":46900,"emoji":"⌚"}
     ],"geofence_radius":300,"color":"#6b7280"},
    {"id":"amb7","name":"Lifestyle Store","category":"lifestyle","lat":17.4164,"lng":78.4353,"rating":4.1,
     "mall":"AMB Mall","floor":"2nd Floor","shop_number":"2F-210",
     "address":"AMB Mall, 2nd Floor, Narsingi","phone":"+91-40-6700-1007",
     "products":[
         {"id":"ls1","name":"Home Decor Set","price":1800,"emoji":"🏮"},
         {"id":"ls2","name":"Scented Candles","price":599,"emoji":"🕯️"},
         {"id":"ls3","name":"Table Runner","price":450,"emoji":"🛋️"},
         {"id":"ls4","name":"Kitchenware Bundle","price":2400,"emoji":"🍳"},
         {"id":"ls5","name":"Decorative Vase","price":899,"emoji":"🌿"}
     ],"geofence_radius":300,"color":"#14b8a6"},
    {"id":"amb8","name":"Starbucks AMB","category":"cafe","lat":17.4150,"lng":78.4348,"rating":4.3,
     "mall":"AMB Mall","floor":"Ground Floor","shop_number":"GF-110",
     "address":"AMB Mall, Ground Floor Entrance","phone":"+91-40-6700-1008",
     "products":[
         {"id":"sb1","name":"Frappuccino","price":380,"emoji":"🧋"},
         {"id":"sb2","name":"Caramel Macchiato","price":350,"emoji":"☕"},
         {"id":"sb3","name":"Iced Matcha Latte","price":360,"emoji":"🍵"},
         {"id":"sb4","name":"Croissant","price":180,"emoji":"🥐"},
         {"id":"sb5","name":"Cake Pop","price":120,"emoji":"🍭"}
     ],"geofence_radius":300,"color":"#16a34a"},
]

OFFER_TEMPLATES = {
    "bakery":[
        {"title":"Fresh Bake Deal","product":"Chocolate Cake","discount":20,"desc":"20% off on freshly baked Chocolate Cake!","validity_hours":4},
        {"title":"Morning Special","product":"Croissant + Coffee","discount":15,"desc":"15% off on Croissants — start your day right!","validity_hours":3},
        {"title":"Buy 2 Get 1","product":"Cookies","discount":33,"desc":"Buy 2 packs of cookies, get 1 FREE!","validity_hours":6},
    ],
    "cafe":[
        {"title":"Coffee Combo","product":"Cappuccino + Muffin","discount":25,"desc":"Cappuccino + Muffin at 25% off!","validity_hours":4},
        {"title":"Happy Hours","product":"Cold Brew","discount":30,"desc":"30% off Cold Brew between 2-5 PM!","validity_hours":3},
        {"title":"Loyalty Boost","product":"Any Beverage","discount":20,"desc":"20% off as a loyalty reward!","validity_hours":8},
    ],
    "supermarket":[
        {"title":"Snack Attack","product":"Snack Combo Pack","discount":15,"desc":"15% off on bestselling snack combos!","validity_hours":6},
        {"title":"Beverage Bundle","product":"4 Beverages","discount":20,"desc":"Buy 4 beverages and save 20%!","validity_hours":4},
        {"title":"Weekend Special","product":"Mixed Nuts","discount":25,"desc":"Healthy snacking at 25% off!","validity_hours":48},
    ],
    "restaurant":[
        {"title":"Lunch Deal","product":"Thali Combo","discount":20,"desc":"Full Thali Combo 20% off between 12-3 PM!","validity_hours":3},
        {"title":"Student Special","product":"Biryani","discount":15,"desc":"Student ID = 15% off Biryani!","validity_hours":8},
        {"title":"Combo Saver","product":"Burger + Lassi","discount":25,"desc":"Burger + Lassi combo 25% off!","validity_hours":5},
    ],
    "convenience_store":[
        {"title":"Daily Essentials","product":"Essentials Kit","discount":10,"desc":"10% off daily essentials!","validity_hours":24},
        {"title":"Hydration Deal","product":"Water Pack","discount":15,"desc":"15% off water packs!","validity_hours":12},
        {"title":"Quick Bite","product":"Chips + Chocolate","discount":20,"desc":"Quick snack combo 20% off!","validity_hours":6},
    ],
    "fashion":[
        {"title":"End of Season Sale","product":"All Clothing","discount":30,"desc":"Up to 30% off on all clothing!","validity_hours":48},
        {"title":"New Arrivals","product":"Summer Collection","discount":15,"desc":"15% off brand new summer arrivals!","validity_hours":24},
        {"title":"Style Bundle","product":"Top + Bottom","discount":20,"desc":"Any top + bottom combo 20% off!","validity_hours":12},
    ],
    "beauty":[
        {"title":"Skincare Sunday","product":"Skincare Kit","discount":25,"desc":"25% off all skincare products!","validity_hours":8},
        {"title":"Fragrance Festival","product":"Perfumes","discount":20,"desc":"20% off all fragrances!","validity_hours":24},
        {"title":"Beauty Bundle","product":"Makeup + Skincare","discount":18,"desc":"Buy 2 makeup, get skincare 18% off!","validity_hours":12},
    ],
    "entertainment":[
        {"title":"Movie Monday","product":"Standard Tickets","discount":20,"desc":"20% off all standard movie tickets!","validity_hours":12},
        {"title":"Couple Combo","product":"2 Tickets + Popcorn","discount":25,"desc":"2 Gold tickets + Popcorn 25% off!","validity_hours":6},
        {"title":"IMAX Weekend","product":"IMAX Experience","discount":15,"desc":"IMAX this weekend — 15% off!","validity_hours":48},
    ],
    "electronics":[
        {"title":"EMI Zero Cost","product":"iPhones","discount":5,"desc":"Zero cost EMI + 5% cashback on iPhones!","validity_hours":24},
        {"title":"Trade-In Bonus","product":"MacBooks","discount":10,"desc":"Extra ₹5000 on laptop trade-in!","validity_hours":72},
        {"title":"AirPods Deal","product":"AirPods Pro","discount":8,"desc":"AirPods Pro 8% off + free engraving!","validity_hours":12},
    ],
    "lifestyle":[
        {"title":"Home Refresh","product":"Decor Bundle","discount":22,"desc":"22% off on home decor bundles!","validity_hours":24},
        {"title":"Kitchen Fest","product":"Kitchenware","discount":18,"desc":"Upgrade your kitchen — 18% off!","validity_hours":48},
        {"title":"Gift Set Special","product":"Gift Boxes","discount":20,"desc":"Perfect gifts at 20% off!","validity_hours":12},
    ]
}

analytics = {
    "geofence_entries":127,"offers_sent":89,"offers_redeemed":43,"revenue":12450,
    "daily_entries":[12,19,8,23,15,28,22],"daily_revenue":[1200,1850,980,2300,1500,2800,1820],
    "category_breakdown":{"bakery":35,"cafe":28,"supermarket":22,"restaurant":15},
    "weekly_visits":[
        {"day":"Mon","visits":45},{"day":"Tue","visits":52},{"day":"Wed","visits":38},
        {"day":"Thu","visits":61},{"day":"Fri","visits":75},{"day":"Sat","visits":98},{"day":"Sun","visits":88}
    ]
}

def get_all_stores():
    return DEMO_STORES + DYNAMIC_STORES

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlam = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_offers_for_store(store, skip_disabled=True):
    category  = store.get("category","supermarket")
    templates = OFFER_TEMPLATES.get(category, OFFER_TEMPLATES["supermarket"])
    offers    = []
    now       = datetime.now()
    products  = store.get("products",[])
    for i, t in enumerate(templates):
        offer_id = f"off_{store['id']}_{i}"
        if skip_disabled and offer_id in DISABLED_OFFERS:
            continue
        if MONGO_OK:
            try:
                setting = db.offer_settings.find_one({"offer_id":offer_id})
                if setting and not setting.get("enabled",True):
                    continue
            except: pass
        p    = products[i % len(products)] if products else {"price":100,"emoji":"🏷️","name":"Product"}
        orig = p["price"]; disc = t["discount"]
        offers.append({
            "id":offer_id,"store_id":store["id"],"store_name":store["name"],
            "title":t["title"],"product":t["product"],"product_emoji":p["emoji"],
            "description":t["desc"],"discount_pct":disc,"original_price":orig,
            "discount_amount":round(orig*disc/100),"final_price":orig-round(orig*disc/100),
            "valid_until":(now+timedelta(hours=t["validity_hours"])).strftime("%I:%M %p"),
            "is_ai_generated":True,"enabled":True,"claimed":False
        })
    # Custom offers from MongoDB
    if MONGO_OK:
        try:
            for co in db.custom_offers.find({"store_id":store["id"],"enabled":True}):
                co.pop("_id",None)
                offers.append(co)
        except: pass
    return offers

def ai_recommendations(user_history, user_lat, user_lng):
    cat_freq = {}
    for item in user_history:
        c = item.get("category",item) if isinstance(item,dict) else item
        cat_freq[c] = cat_freq.get(c,0)+1
    top_cats = sorted(cat_freq, key=lambda c: cat_freq[c], reverse=True)[:3]
    recs = []
    for s in get_all_stores():
        if s["category"] in top_cats or not top_cats:
            dist   = haversine(user_lat, user_lng, s["lat"], s["lng"])
            offers = get_offers_for_store(s)
            if offers:
                recs.append({
                    "store_id":s["id"],"store_name":s["name"],"category":s["category"],
                    "distance":round(dist),"rating":s["rating"],"top_offer":offers[0],
                    "reason":f"Based on your interest in {s['category']}"
                })
    return sorted(recs, key=lambda x: x["distance"])[:6]

# ── PAGE ROUTES ───────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', razorpay_key=RAZORPAY_KEY_ID)

@app.route('/login')
def login_page():
    return render_template('login.html', google_client_id=GOOGLE_CLIENT_ID)

@app.route('/map')
def map_page():
    return render_template('map.html')

@app.route('/explore')
def explore_page():
    return render_template('explore.html')

@app.route('/store/<store_id>')
def store_detail(store_id):
    return render_template('store_detail.html', store_id=store_id)

@app.route('/offers')
def offers_page():
    return render_template('offers.html')

@app.route('/dashboard')
def user_dashboard():
    return render_template('dashboard.html')

@app.route('/retailer')
def retailer_dashboard():
    return render_template('retailer.html', razorpay_key=RAZORPAY_KEY_ID)

@app.route('/billing')
def billing_page():
    return render_template('billing.html', razorpay_key=RAZORPAY_KEY_ID)

@app.route('/messages')
def messages_page():
    return render_template('messages.html')

# ── AUTH APIs ─────────────────────────────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email','').lower()
    password = data.get('password','')
    user = None
    if MONGO_OK:
        try:
            user = db.users.find_one({"email":email})
            if user:
                stored = user.get("password","")
                if stored != password and stored != hash_password(password):
                    return jsonify({"success":False,"message":"Invalid credentials"}),401
        except: pass
    if not user:
        demo = {
            "demo@smartaisle.com":{"id":"u1","name":"Alex Johnson","email":"demo@smartaisle.com","password":"demo123","role":"user","purchase_history":["bakery","cafe"],"points":1250,"tier":"Gold"},
            "retailer@smartaisle.com":{"id":"r1","name":"Store Manager","email":"retailer@smartaisle.com","password":"retail123","role":"retailer","points":0,"tier":"Bronze"},
        }
        u = demo.get(email)
        if not u or u['password'] != password:
            return jsonify({"success":False,"message":"Invalid credentials"}),401
        user = u
    user_id = str(user.get("id") or user.get("_id",""))
    resp = {"id":user_id,"name":user.get("name",""),"email":user.get("email",""),
            "role":user.get("role","user"),"points":user.get("points",0),
            "tier":user.get("tier","Bronze"),"purchase_history":user.get("purchase_history",[]),
            "avatar":user.get("avatar","")}
    if MONGO_OK:
        try: db.users.update_one({"email":email},{"$set":{"last_login":datetime.now().isoformat()}})
        except: pass
    return jsonify({"success":True,"user":resp})

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    data  = request.json
    email = data.get('email','').lower()
    if MONGO_OK:
        try:
            if db.users.find_one({"email":email}):
                return jsonify({"success":False,"message":"Email already registered"}),400
        except: pass
    elif email in _mem_users:
        return jsonify({"success":False,"message":"Email already registered"}),400
    uid  = str(uuid.uuid4())[:8]
    new_user = {"id":uid,"name":data.get('name','User'),"email":email,
                "password":data.get('password',''),"role":data.get('role','user'),
                "purchase_history":[],"points":0,"tier":"Bronze",
                "created_at":datetime.now().isoformat(),"avatar":""}
    if MONGO_OK:
        try: db.users.insert_one(new_user.copy())
        except: pass
    else:
        _mem_users[email] = new_user
    resp = {k:v for k,v in new_user.items() if k != 'password'}
    return jsonify({"success":True,"user":resp})

@app.route('/api/auth/google', methods=['POST'])
def api_google_auth():
    data        = request.json
    google_user = data.get('user',{})
    if not google_user.get('email'):
        return jsonify({"success":False,"message":"Invalid Google user data"}),400
    email  = google_user['email'].lower()
    uid    = google_user.get('id', str(uuid.uuid4())[:8])
    name   = google_user.get('name','Google User')
    avatar = google_user.get('picture','')
    user_doc = {"id":uid,"name":name,"email":email,"password":"","role":"user",
                "purchase_history":[],"points":0,"tier":"Bronze","avatar":avatar,
                "google_id":uid,"created_at":datetime.now().isoformat()}
    if MONGO_OK:
        try:
            existing = db.users.find_one({"email":email})
            if not existing:
                db.users.insert_one(user_doc.copy())
            else:
                db.users.update_one({"email":email},{"$set":{"avatar":avatar,"name":name}})
                user_doc = {**user_doc, **{k:v for k,v in existing.items() if k != '_id'}}
        except: pass
    resp = {k:v for k,v in user_doc.items() if k not in ('password','_id')}
    return jsonify({"success":True,"user":resp})

# ── STORE APIs ────────────────────────────────────────────────────────────────
@app.route('/api/stores/all')
def all_stores():
    return jsonify({"success":True,"stores":get_all_stores()})

@app.route('/api/stores/nearby', methods=['POST'])
def nearby_stores():
    d=request.json; lat=float(d.get('lat',17.4401)); lng=float(d.get('lng',78.4987))
    radius=float(d.get('radius',1000)); mall=d.get('mall'); cat=d.get('category')
    result=[]
    for s in get_all_stores():
        if mall and s.get('mall')!=mall: continue
        if cat and s.get('category')!=cat: continue
        dist=haversine(lat,lng,s['lat'],s['lng'])
        if dist<=radius:
            sc=dict(s); sc['distance']=round(dist); sc['in_geofence']=dist<=s['geofence_radius']
            result.append(sc)
    result.sort(key=lambda x:x['distance'])
    return jsonify({"success":True,"stores":result})

@app.route('/api/stores/<store_id>')
def get_store(store_id):
    s=next((s for s in get_all_stores() if s['id']==store_id),None)
    if not s: return jsonify({"success":False}),404
    lat=float(request.args.get('lat',17.4401)); lng=float(request.args.get('lng',78.4987))
    dist=haversine(lat,lng,s['lat'],s['lng'])
    sc=dict(s); sc['distance']=round(dist); sc['in_geofence']=dist<=s['geofence_radius']
    sc['offers']=get_offers_for_store(s)
    return jsonify({"success":True,"store":sc})

@app.route('/api/stores/search')
def search_stores():
    q=request.args.get('q','').lower(); mall=request.args.get('mall','').lower()
    cat=request.args.get('category','').lower(); results=[]
    for s in get_all_stores():
        if cat and s['category'].lower()!=cat: continue
        if (q in s['name'].lower() or q in s.get('mall','').lower() or
            q in s['category'].lower() or q in s.get('address','').lower()) or \
           (mall and mall in s.get('mall','').lower()):
            results.append(s)
    return jsonify({"success":True,"stores":results,"count":len(results)})

@app.route('/api/stores/malls')
def get_malls():
    malls={}
    for s in get_all_stores():
        m=s.get('mall','Other')
        if m not in malls: malls[m]={"name":m,"stores":[],"lat":s['lat'],"lng":s['lng']}
        malls[m]["stores"].append({"id":s["id"],"name":s["name"],"category":s["category"],"floor":s.get("floor",""),"rating":s["rating"]})
    return jsonify({"success":True,"malls":list(malls.values())})

@app.route('/api/stores/register', methods=['POST'])
def register_store():
    d=request.json
    new_store={"id":f"dyn_{uuid.uuid4().hex[:6]}","name":d.get('name','New Store'),
               "category":d.get('category','supermarket'),"lat":float(d.get('lat',17.4401)),
               "lng":float(d.get('lng',78.4987)),"rating":4.0,"mall":d.get('mall',''),
               "floor":d.get('floor',''),"shop_number":d.get('shop_number',''),
               "address":d.get('address',''),"phone":d.get('phone',''),"products":[],
               "geofence_radius":int(d.get('geofence_radius',200)),"color":"#6366f1",
               "owner_id":d.get('owner_id','')}
    DYNAMIC_STORES.append(new_store)
    if MONGO_OK:
        try: db.stores.insert_one(new_store.copy())
        except: pass
    return jsonify({"success":True,"store":new_store})

@app.route('/api/stores/<store_id>/products', methods=['GET','POST'])
def store_products(store_id):
    if request.method=='GET':
        s=next((s for s in get_all_stores() if s['id']==store_id),None)
        prods=list(s.get("products",[])) if s else []
        if MONGO_OK:
            try:
                for p in db.products.find({"store_id":store_id}):
                    p.pop('_id',None); prods.append(p)
            except: pass
        return jsonify({"success":True,"products":prods})
    else:
        d=request.json
        new_prod={"id":f"prod_{uuid.uuid4().hex[:6]}","store_id":store_id,
                  "name":d.get('name','Product'),"price":float(d.get('price',100)),
                  "emoji":d.get('emoji','🛍️'),"category":d.get('category',''),
                  "description":d.get('description',''),"stock":int(d.get('stock',100))}
        if MONGO_OK:
            try: db.products.insert_one(new_prod.copy())
            except: pass
        s=next((s for s in get_all_stores() if s['id']==store_id),None)
        if s: s.setdefault("products",[]).append(new_prod)
        return jsonify({"success":True,"product":new_prod})

# ── OFFER APIs ────────────────────────────────────────────────────────────────
@app.route('/api/offers/all')
def all_offers():
    all_off=[]
    for s in get_all_stores(): all_off.extend(get_offers_for_store(s))
    return jsonify({"success":True,"offers":all_off,"count":len(all_off)})

@app.route('/api/offers/generate', methods=['POST'])
def generate_offers():
    d=request.json; lat=float(d.get('lat',17.4401)); lng=float(d.get('lng',78.4987))
    store_id=d.get('store_id'); all_off=[]
    stores=[s for s in get_all_stores() if s['id']==store_id] if store_id else get_all_stores()
    for s in stores:
        dist=haversine(lat,lng,s['lat'],s['lng'])
        if dist<=s['geofence_radius'] or store_id:
            all_off.extend(get_offers_for_store(s)); analytics["offers_sent"]+=1
    return jsonify({"success":True,"offers":all_off})

@app.route('/api/offers/claim', methods=['POST'])
def claim_offer():
    d=request.json; offer_id=d.get('offer_id'); store_id=d.get('store_id'); user_id=d.get('user_id','guest')
    s=next((s for s in get_all_stores() if s['id']==store_id),None)
    if not s: return jsonify({"success":False,"message":"Store not found"}),404
    offers=get_offers_for_store(s)
    offer=next((o for o in offers if o['id']==offer_id),None)
    if not offer: return jsonify({"success":False,"message":"Offer not found"}),404
    claimed={"id":str(uuid.uuid4()),"offer_id":offer_id,"store_id":store_id,"user_id":user_id,
             "offer":offer,"claimed_at":datetime.now().isoformat(),"used":False}
    if MONGO_OK:
        try: db.claimed_offers.insert_one(claimed.copy())
        except: pass
    _mem_claimed_offers.append(claimed)
    analytics["offers_redeemed"]+=1
    return jsonify({"success":True,"message":"Offer claimed! Applied at checkout.","offer":offer,"claim_id":claimed["id"]})

@app.route('/api/offers/claimed/<user_id>')
def get_claimed_offers(user_id):
    claimed=[]
    if MONGO_OK:
        try:
            for c in db.claimed_offers.find({"user_id":user_id,"used":False}):
                c.pop('_id',None); claimed.append(c)
        except: pass
    if not claimed:
        claimed=[c for c in _mem_claimed_offers if c.get('user_id')==user_id and not c.get('used')]
    return jsonify({"success":True,"claimed":claimed})

@app.route('/api/offers/toggle', methods=['POST'])
def toggle_offer():
    d=request.json; offer_id=d.get('offer_id'); enabled=d.get('enabled',True)
    if not enabled: DISABLED_OFFERS.add(offer_id)
    else: DISABLED_OFFERS.discard(offer_id)
    if MONGO_OK:
        try: db.offer_settings.update_one({"offer_id":offer_id},{"$set":{"enabled":enabled}},upsert=True)
        except: pass
    socketio.emit('offer_toggled',{"offer_id":offer_id,"enabled":enabled})
    return jsonify({"success":True,"offer_id":offer_id,"enabled":enabled})

@app.route('/api/offers/custom', methods=['POST'])
def add_custom_offer():
    d=request.json
    new_offer={"id":f"custom_{uuid.uuid4().hex[:6]}","store_id":d.get('store_id'),
               "title":d.get('title','Special Offer'),"product":d.get('product',''),
               "product_emoji":d.get('emoji','🏷️'),"description":d.get('description',''),
               "discount_pct":int(d.get('discount_pct',10)),"original_price":float(d.get('original_price',100)),
               "enabled":True,"is_custom":True,"created_at":datetime.now().isoformat()}
    new_offer["discount_amount"]=round(new_offer["original_price"]*new_offer["discount_pct"]/100)
    new_offer["final_price"]=new_offer["original_price"]-new_offer["discount_amount"]
    new_offer["valid_until"]=d.get('valid_until','')
    if MONGO_OK:
        try: db.custom_offers.insert_one(new_offer.copy())
        except: pass
    return jsonify({"success":True,"offer":new_offer})

# ── GEOFENCE ──────────────────────────────────────────────────────────────────
@app.route('/api/geofence/check', methods=['POST'])
def check_geofence():
    d=request.json; lat=float(d.get('lat')); lng=float(d.get('lng'))
    triggered=[]
    for s in get_all_stores():
        dist=haversine(lat,lng,s['lat'],s['lng'])
        if dist<=s['geofence_radius']:
            offers=get_offers_for_store(s)
            triggered.append({
                "store_id":s["id"],"store_name":s["name"],"category":s["category"],
                "distance":round(dist),"offers":offers[:1],
                "notification_title":"🎯 Special Offer Nearby!",
                "notification_body":f"You're near {s['name']}! {offers[0]['description'] if offers else 'Check out deals!'}"
            })
            analytics["geofence_entries"]+=1
            if MONGO_OK:
                try: db.store_visits.insert_one({"store_id":s["id"],"store_name":s["name"],"lat":lat,"lng":lng,"timestamp":datetime.now().isoformat()})
                except: pass
    return jsonify({"success":True,"triggered":triggered,"count":len(triggered)})

# ── ORDERS & MESSAGING ───────────────────────────────────────────────────────
@app.route('/api/orders', methods=['POST'])
def create_order():
    d=request.json
    order={"id":f"ORD-{uuid.uuid4().hex[:8].upper()}","user_id":d.get('user_id','guest'),
           "user_name":d.get('user_name','Customer'),"retailer_id":d.get('retailer_id',''),
           "store_name":d.get('store_name',''),"items":d.get('items',[]),
           "subtotal":d.get('subtotal',0),"discount":d.get('discount',0),"total":d.get('total',0),
           "payment_id":d.get('payment_id',''),"status":"placed","created_at":datetime.now().isoformat()}
    if MONGO_OK:
        try: db.orders.insert_one(order.copy())
        except: pass
    _mem_orders.append(order)
    # Auto-message retailer
    items_str=", ".join([i.get('name','') for i in order['items']])
    msg={"id":str(uuid.uuid4()),"order_id":order["id"],"sender":"system",
         "receiver":order["retailer_id"] or "retailer","type":"new_order",
         "message":f"🛒 New Order #{order['id']}\nCustomer: {order['user_name']}\nItems: {items_str}\nTotal: ₹{order['total']}",
         "timestamp":datetime.now().isoformat(),"read":False}
    if MONGO_OK:
        try: db.messages.insert_one(msg.copy())
        except: pass
    _mem_messages.append(msg)
    socketio.emit('new_order',order,room=order.get('retailer_id','retailer'))
    socketio.emit('new_message',msg,room=order.get('retailer_id','retailer'))
    return jsonify({"success":True,"order":order})

@app.route('/api/orders/<user_id>')
def get_orders(user_id):
    orders=[]
    if MONGO_OK:
        try:
            for o in db.orders.find({"user_id":user_id}).sort("created_at",DESCENDING).limit(50):
                o.pop('_id',None); orders.append(o)
        except: pass
    if not orders: orders=[o for o in _mem_orders if o.get('user_id')==user_id]
    return jsonify({"success":True,"orders":orders})

@app.route('/api/orders/retailer/<retailer_id>')
def get_retailer_orders(retailer_id):
    orders=[]
    if MONGO_OK:
        try:
            for o in db.orders.find({"retailer_id":retailer_id}).sort("created_at",DESCENDING).limit(100):
                o.pop('_id',None); orders.append(o)
        except: pass
    if not orders:
        orders=[o for o in _mem_orders if o.get('retailer_id')==retailer_id]
        if not orders: orders=_mem_orders[-20:]
    return jsonify({"success":True,"orders":orders})

@app.route('/api/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    d=request.json; status=d.get('status','confirmed')
    msg_text={"confirmed":"✅ Your order is confirmed!","preparing":"👨‍🍳 Order is being prepared.",
              "ready":"🎉 Your order is ready!","delivered":"📦 Order delivered!"}.get(status,f"Status: {status}")
    if MONGO_OK:
        try: db.orders.update_one({"id":order_id},{"$set":{"status":status}})
        except: pass
    for o in _mem_orders:
        if o.get('id')==order_id: o['status']=status
    order=next((o for o in _mem_orders if o.get('id')==order_id),{})
    if MONGO_OK and not order:
        try:
            order=db.orders.find_one({"id":order_id}) or {}
        except: pass
    if order:
        msg={"id":str(uuid.uuid4()),"order_id":order_id,"sender":"retailer",
             "receiver":order.get('user_id',''),"type":"order_update","message":msg_text,
             "timestamp":datetime.now().isoformat(),"read":False}
        if MONGO_OK:
            try: db.messages.insert_one(msg.copy())
            except: pass
        _mem_messages.append(msg)
        socketio.emit('order_update',{"order_id":order_id,"status":status,"message":msg_text},room=order.get('user_id',''))
        socketio.emit('new_message',msg,room=order.get('user_id',''))
    return jsonify({"success":True,"status":status})

@app.route('/api/messages/<user_id>')
def get_messages(user_id):
    msgs=[]
    if MONGO_OK:
        try:
            for m in db.messages.find({"$or":[{"receiver":user_id},{"sender":user_id}]}).sort("timestamp",DESCENDING).limit(100):
                m.pop('_id',None); msgs.append(m)
        except: pass
    if not msgs:
        msgs=[m for m in _mem_messages if m.get('receiver')==user_id or m.get('sender')==user_id]
        msgs=sorted(msgs,key=lambda x:x.get('timestamp',''),reverse=True)
    return jsonify({"success":True,"messages":msgs})

@app.route('/api/messages/send', methods=['POST'])
def send_message():
    d=request.json
    msg={"id":str(uuid.uuid4()),"order_id":d.get('order_id',''),"sender":d.get('sender',''),
         "receiver":d.get('receiver',''),"type":d.get('type','chat'),"message":d.get('message',''),
         "timestamp":datetime.now().isoformat(),"read":False}
    if MONGO_OK:
        try: db.messages.insert_one(msg.copy())
        except: pass
    _mem_messages.append(msg)
    socketio.emit('new_message',msg,room=msg['receiver'])
    return jsonify({"success":True,"message":msg})

# ── PAYMENT ───────────────────────────────────────────────────────────────────
@app.route('/api/payment/create-order', methods=['POST'])
def create_payment_order():
    d=request.json; amount=int(d.get('amount',100))
    try:
        import razorpay
        client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))
        order=client.order.create({"amount":amount*100,"currency":"INR","receipt":f"rcpt_{uuid.uuid4().hex[:8]}","notes":{"platform":"ShopVerse"}})
        return jsonify({"success":True,"order":order,"key":RAZORPAY_KEY_ID})
    except Exception as e:
        return jsonify({"success":True,"order":{"id":f"order_{uuid.uuid4().hex[:10]}","amount":amount*100,"currency":"INR"},"key":RAZORPAY_KEY_ID,"mock":True})

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    d=request.json
    # For demo always succeed
    return jsonify({"success":True,"payment_id":d.get('razorpay_payment_id','demo_pay'),"verified":True})

@app.route('/api/billing/checkout', methods=['POST'])
def checkout():
    d=request.json; items=d.get('items',[]); user_id=d.get('user_id','guest')
    subtotal=sum(i.get('original_price',i.get('price',0)) for i in items)
    disc_tot=sum(i.get('discount_amount',0) for i in items)
    final=subtotal-disc_tot
    if MONGO_OK:
        try: db.claimed_offers.update_many({"user_id":user_id,"used":False},{"$set":{"used":True}})
        except: pass
    for c in _mem_claimed_offers:
        if c.get('user_id')==user_id: c['used']=True
    pts=int(final/10)
    if MONGO_OK:
        try: db.users.update_one({"id":user_id},{"$inc":{"points":pts}})
        except: pass
    analytics["revenue"]+=final
    bill={"items":items,"subtotal":subtotal,"discount_total":disc_tot,"final_total":final,
          "points_earned":pts,"order_id":f"ORD-{uuid.uuid4().hex[:8].upper()}",
          "payment_id":d.get('payment_id',''),"timestamp":datetime.now().isoformat()}
    return jsonify({"success":True,"bill":bill})

# ── ANALYTICS ─────────────────────────────────────────────────────────────────
@app.route('/api/analytics')
def get_analytics():
    data=dict(analytics)
    if MONGO_OK:
        try:
            data["total_visits"]=db.store_visits.count_documents({})
            data["total_orders"]=db.orders.count_documents({})
        except: pass
    return jsonify({"success":True,"analytics":data})

@app.route('/api/analytics/heatmap')
def heatmap_data():
    # Weekly + hourly heatmap data
    heatmap = []
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    base = [45,52,38,61,75,98,88]
    for i,day in enumerate(days):
        hours = []
        b = base[i]
        for h in range(24):
            # Peak hours: 10-13, 17-21
            if 10<=h<=13 or 17<=h<=21:
                hours.append(int(b*random.uniform(0.6,1.0)))
            elif 7<=h<=9:
                hours.append(int(b*random.uniform(0.2,0.4)))
            else:
                hours.append(int(b*random.uniform(0.05,0.15)))
        heatmap.append({"day":day,"visits":base[i],"hours":hours})
    return jsonify({"success":True,"heatmap":heatmap})

# ── RECOMMENDATIONS ──────────────────────────────────────────────────────────
@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    d=request.json; user_id=d.get('user_id','')
    lat=float(d.get('lat',17.4401)); lng=float(d.get('lng',78.4987))
    history=[]
    if MONGO_OK:
        try:
            user=db.users.find_one({"id":user_id})
            if user: history=user.get('purchase_history',[])
        except: pass
    recs=ai_recommendations(history,lat,lng)
    return jsonify({"success":True,"recommendations":recs})

# ── AI CHAT ───────────────────────────────────────────────────────────────────
@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    d=request.json; query=d.get('query','')
    lat=float(d.get('lat',17.4401)); lng=float(d.get('lng',78.4987))
    history=d.get('history',[])
    stores_context=[]
    for s in get_all_stores():
        dist=haversine(lat,lng,s['lat'],s['lng'])
        offers=get_offers_for_store(s)
        stores_context.append({
            "name":s["name"],"category":s["category"],"mall":s.get("mall",""),
            "floor":s.get("floor",""),"rating":s["rating"],"distance_m":round(dist),
            "active_offers":[f"{o['title']}: {o['discount_pct']}% off {o['product']}" for o in offers[:2]]
        })
    system_prompt=f"""You are ShopVerseAI — AI assistant for ShopVerse smart shopping platform, Hyderabad.
You help users find stores, deals, navigate malls and get personalized recommendations.
Current location: {lat:.4f},{lng:.4f}
Stores: {json.dumps(stores_context[:10],indent=1)}
Be concise, helpful, use emojis. For navigation: <action>{{"type":"navigate","url":"/map"}}</action>
Mention prices and discounts. Max 150 words."""
    messages=[{"role":h["role"],"content":h["content"]} for h in history[-6:]]
    messages.append({"role":"user","content":query})
    try:
        import anthropic
        api_key=os.environ.get('ANTHROPIC_API_KEY','')
        if not api_key: raise Exception("no key")
        client=anthropic.Anthropic(api_key=api_key)
        message=client.messages.create(model="claude-opus-4-5",max_tokens=400,system=system_prompt,messages=messages)
        text=message.content[0].text; action=None
        m=re.search(r'<action>(.*?)</action>',text,re.DOTALL)
        if m:
            try: action=json.loads(m.group(1))
            except: pass
            text=text.replace(m.group(0),'').strip()
        relevant=[s for s in get_all_stores() if s['name'].lower() in text.lower() or s['category'].lower() in query.lower()]
        return jsonify({"success":True,"response":text,"stores":relevant[:4],"action":action})
    except:
        return fallback_chat_response(query,lat,lng)

def fallback_chat_response(query,lat,lng):
    ql=query.lower(); text=""; sug=[]; stores=[]; action=None
    if any(w in ql for w in ['amb','narsingi']):
        stores=[s for s in get_all_stores() if s.get('mall')=='AMB Mall']
        text=f"🏬 AMB Mall has {len(stores)} stores — fashion, food, beauty, cinema & more! All have active deals."
        sug=["AMB Mall deals","Fashion stores","Food court","Cinema"]
    elif any(w in ql for w in ['bakery','cake','croissant','pastry']):
        stores=[s for s in get_all_stores() if s['category']=='bakery']
        text="🥐 Campus Bakery — 20% off Chocolate Cake today! Buy 2 Cookies get 1 free!"
    elif any(w in ql for w in ['coffee','cafe','starbucks']):
        stores=[s for s in get_all_stores() if s['category']=='cafe']
        text="☕ Starbucks AMB (GF-110): Frappuccino 25% off! Coffee Lab: 30% off Cold Brew!"
    elif any(w in ql for w in ['fashion','clothes','clothing','zara']):
        stores=[s for s in get_all_stores() if s['category']=='fashion']
        text="👗 Zara End of Season Sale — 30% off! H&M New Arrivals — 15% off!"
    elif any(w in ql for w in ['food','eat','biryani','restaurant','hungry']):
        stores=[s for s in get_all_stores() if s['category']=='restaurant']
        text="🍛 Food Hall AMB (3F, ⭐4.7): Hyderabadi Biryani ₹250! Spice Garden: Thali 20% off!"
    elif any(w in ql for w in ['electronics','apple','iphone','phone']):
        stores=[s for s in get_all_stores() if s['category']=='electronics']
        text="📱 Apple Store AMB (1F-108): Zero-cost EMI on iPhones! MacBook trade-in extra ₹5000."
    elif any(w in ql for w in ['offer','deal','discount','sale']):
        text="🏷️ Amazing deals everywhere! AMB Mall: fashion 30% off, food 20% off, beauty 25% off!"
        action={"type":"navigate","url":"/offers"}
    elif any(w in ql for w in ['map','navigate','where']):
        text="🗺️ Opening map! Search any location — AMB Mall, Ameerpet, Banjara Hills..."
        action={"type":"navigate","url":"/map"}
    elif any(w in ql for w in ['checkout','cart','pay','billing']):
        text="💳 Going to checkout! Your claimed offers are applied automatically."
        action={"type":"navigate","url":"/billing"}
    else:
        text="👋 Hi! I'm ShopVerseAI. Ask about stores, offers, navigation or any product!"
        sug=["AMB Mall stores","Best offers today","Food court","Fashion deals"]
    return jsonify({"success":True,"response":text,"suggestions":sug,"stores":stores[:4],"action":action})

@app.route('/api/geocode')
def geocode():
    q=request.args.get('q','')
    try:
        import requests as req
        resp=req.get(f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=8&addressdetails=1",headers={'User-Agent':'ShopVerse/1.0'},timeout=10)
        results=resp.json()
        locs=[{"display_name":r.get("display_name",""),"lat":float(r["lat"]),"lng":float(r["lon"])} for r in results]
        return jsonify({"success":True,"locations":locs})
    except:
        fallback={"amb mall":{"lat":17.4156,"lng":78.4347,"display_name":"AMB Mall, Narsingi, Hyderabad"},
                  "ameerpet":{"lat":17.4374,"lng":78.4474,"display_name":"Ameerpet, Hyderabad"},
                  "banjara hills":{"lat":17.4126,"lng":78.4485,"display_name":"Banjara Hills, Hyderabad"},
                  "jubilee hills":{"lat":17.4314,"lng":78.4066,"display_name":"Jubilee Hills, Hyderabad"},
                  "madhapur":{"lat":17.4483,"lng":78.3915,"display_name":"Madhapur, Hyderabad"},
                  "hitech city":{"lat":17.4435,"lng":78.3772,"display_name":"Hitech City, Hyderabad"},
                  "college campus":{"lat":17.4401,"lng":78.4987,"display_name":"College Campus, Hyderabad"},
                  "hyderabad":{"lat":17.3850,"lng":78.4867,"display_name":"Hyderabad, Telangana"}}
        ql=q.lower()
        for k,v in fallback.items():
            if k in ql: return jsonify({"success":True,"locations":[v]})
        return jsonify({"success":True,"locations":[]})

# ── USERS ─────────────────────────────────────────────────────────────────────
@app.route('/api/users/<user_id>')
def get_user(user_id):
    if MONGO_OK:
        try:
            u=db.users.find_one({"id":user_id})
            if u: u.pop('_id',None); u.pop('password',None); return jsonify({"success":True,"user":u})
        except: pass
    return jsonify({"success":False}),404

@app.route('/api/users/<user_id>/history', methods=['POST'])
def update_history(user_id):
    d=request.json; cat=d.get('category','')
    if MONGO_OK:
        try: db.users.update_one({"id":user_id},{"$addToSet":{"purchase_history":cat}})
        except: pass
    return jsonify({"success":True})

# ── SOCKET.IO ─────────────────────────────────────────────────────────────────
@socketio.on('connect')
def on_connect(): pass

@socketio.on('join')
def on_join(d):
    room=d.get('room','')
    if room: join_room(room)

@socketio.on('leave')
def on_leave(d):
    room=d.get('room','')
    if room: leave_room(room)

@socketio.on('message')
def on_message(d):
    if d.get('receiver'): emit('new_message',d,room=d['receiver'])

if __name__=='__main__':
    port=int(os.environ.get('PORT',5000))
    socketio.run(app,host='0.0.0.0',port=port,debug=True)
