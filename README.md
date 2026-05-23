# Copper Spoon 🥄

A conversational AI host for restaurants. Guests get a natural, friendly experience — browse the menu, book a table, place an order, or leave feedback. Staff get a clean dashboard to manage it all in real time. No app downloads. No clunky interfaces. Just a fast, installable web experience that works on any device.

---

## What it does

**For guests**
- Chat with an AI host that actually sounds human — not a support bot
- Ask about the menu, get dish recommendations by mood, check dietary tags
- Book a table, place an order, track it by confirmation ID, or leave a review
- Responds in 11 languages: Spanish, French, Italian, German, Japanese, Arabic, Turkish, Portuguese, Chinese, Korean, and Hindi

**For staff**
- Admin dashboard for managing live orders and updating their status
- Menu edits (in `data/menu.json`) show up for guests instantly — no restart needed
- Protected routes with session-based authentication

---

## Tech stack

- **Backend** — Flask (Python)
- **AI** — Llama 3.1 via Groq API
- **Database** — Firestore (+ local JSON fallback for reservations, orders, feedback)
- **Frontend** — PWA with dark/light mode, works on desktop, tablet, and mobile

---

## Getting started

```bash
# 1. (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Set your Groq API key
export GROQ_API_KEY=your_key_here

# 3. Run the app
python web.py
```

The app will be live at `http://localhost:5000`.

---

## Environment variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Required. Enables the Llama 3.1 chat client via Groq |
| `RESTAURANT_NAME` | Your restaurant's name |
| `RESTAURANT_CUISINE` | Style of food you serve |
| `RESTAURANT_VIBE` | Atmosphere the AI host should reflect |
| `RESTAURANT_HIGHLIGHTS` | Signature dishes or menu highlights |
| `RESTAURANT_HOURS` | Opening hours shown in the AI prompt |
| `RESTAURANT_PHONE` | Contact number used in the AI prompt |
| `RESTAURANT_RESERVATION_NOTE` | Short reservation policy note |
| `FLASK_SECRET_KEY` | Session signing key |
| `ADMIN_USERNAME` | Override admin username (default: `admin`) |
| `ADMIN_PASSWORD` | Override admin password (default: `copper2026`) |

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main web app |
| `GET` | `/api/menu` | Full menu data |
| `GET` | `/api/menu/search?q=...&tag=...` | Search and filter menu |
| `POST` | `/api/chat` | Send a chat message |
| `POST` | `/api/chat/reset` | Reset conversation |
| `POST` | `/api/reservations` | Create a reservation |
| `POST` | `/api/feedback` | Submit guest feedback |
| `GET` | `/api/feedback/recent` | Recent reviews and stats |
| `POST` | `/api/orders` | Place an order |
| `GET` | `/api/orders/<id>` | Look up order status |
| `POST` | `/admin/login` | Admin login |
| `POST` | `/admin/logout` | Admin logout |
| `GET` | `/admin/check` | Check admin session |
| `GET` | `/api/orders/recent` | Recent orders (admin only) |
| `PUT` | `/api/orders/<id>/status` | Update order status (admin only) |

---

## CLI mode

Run `python cli.py` to chat with the assistant in your terminal.

- `/reset` — clears the conversation
- `quit` or `exit` — closes the session

---

## Notes

- Reservations → `data/reservations.json`
- Orders → `data/orders.json`
- Feedback → `data/feedback.json`
- Tests use Python's built-in `unittest` — no extra dependencies needed
- The PWA is installable on mobile and desktop, with offline caching via service worker
