# ShopVerse — AI-Powered Smart Shopping Platform

A complete full-stack web application built with Flask, MongoDB, Razorpay, Google Auth, and Socket.IO.

## Features

- 🗺️ **Explore Page** — Location-based store discovery (any place in Hyderabad)
- 🤖 **AI Chat & Voice Assistant** — Multilingual, works on every page
- 🛍️ **Category Search** — Filter by bakery, cafe, fashion, electronics, etc.
- 📍 **Geofence Notifications** — Real-time popup when near a store
- 🎟️ **Offer Claim System** — Claims saved to DB, auto-applied at checkout
- 📊 **Analytics Heatmap** — Weekly visit heatmap + bar charts
- ⚙️ **Offer Management** — Admin can add/edit/disable offers (hidden site-wide when disabled)
- 🍕 **Dynamic Products** — Add any product dynamically via retailer panel
- 🔐 **Google Authentication** — One-click Google sign-in
- 🗄️ **MongoDB Integration** — Full persistence for users, orders, offers, messages
- 💳 **Razorpay Payments** — Secure checkout with auto offer application
- 💬 **Real-time Messaging** — User ↔ Retailer via Socket.IO
- 📱 **Fully Responsive** — Works on mobile, tablet, desktop

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Jinja2 + Vanilla JS + CSS |
| Backend | Flask + Socket.IO |
| Database | MongoDB Atlas |
| Auth | Google OAuth 2.0 |
| Payments | Razorpay |
| Real-time | Socket.IO (flask-socketio) |
| Maps | Leaflet.js + OpenStreetMap |

## Setup & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env` and fill in your keys:
```env
MONGODB_URI=mongodb+srv://praneetaphani_db_user:phani@shopverse.6ufzvam.mongodb.net/
RAZORPAY_KEY_ID=rzp_live_SKKoU0dKi4yqx3
RAZORPAY_KEY_SECRET=iZjR3mZES8i6kOKn7EGO0Gy2
GOOGLE_CLIENT_ID=AIzaSyCNxbtSOKe8XCkSk6lPHSfs0wt6Jx2MWDI
ANTHROPIC_API_KEY=your_anthropic_key_here (optional, for AI chat)
SECRET_KEY=your-random-secret-key
PORT=5000
```

### 3. Run Locally
```bash
python app.py
```
Visit: http://localhost:5000

## Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Customer | demo@smartaisle.com | demo123 |
| Retailer | retailer@smartaisle.com | retail123 |

## Deployment (Render / Railway / Heroku)

1. Set all environment variables in your hosting dashboard
2. Set start command: `gunicorn -w 2 -k eventlet app:app`
3. Port is auto-detected via `PORT` env variable

## MongoDB Collections

- `users` — User profiles, purchase history, points
- `orders` — Order details, status, items
- `messages` — User-retailer messaging
- `claimed_offers` — Claimed offers linked to users
- `store_visits` — Geofence entry tracking
- `products` — Dynamic products added by retailers
- `custom_offers` — Admin-created custom offers
- `offer_settings` — Offer enabled/disabled flags

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/login` | Email login |
| POST | `/api/auth/signup` | Register |
| POST | `/api/auth/google` | Google OAuth |
| GET | `/api/stores/all` | All stores |
| POST | `/api/stores/nearby` | Stores within radius |
| GET | `/api/offers/all` | All active offers |
| POST | `/api/offers/claim` | Claim an offer |
| GET | `/api/offers/claimed/:uid` | Get user's claimed offers |
| POST | `/api/offers/toggle` | Enable/disable offer (admin) |
| POST | `/api/payment/create-order` | Razorpay order |
| POST | `/api/payment/verify` | Verify payment |
| POST | `/api/orders` | Create order |
| PUT | `/api/orders/:id/status` | Update order status |
| GET | `/api/messages/:uid` | Get messages |
| POST | `/api/messages/send` | Send message |
| POST | `/api/recommendations` | AI recommendations |
| POST | `/api/ai/chat` | AI chat response |
| GET | `/api/analytics` | Analytics data |
| GET | `/api/analytics/heatmap` | Weekly heatmap |
