# Piano Parts Inventory App

## Goal
Organize hundreds of small parts for a piano repair shop. Track where every part is, how many are in stock, and when to reorder.

---

## Core Data

- **Parts** — name, description, auto-generated part number, category, photo, quantity on hand, cost
- **Bins/Locations** — shelf, row, bin number, QR code for each bin
- **Suppliers** — vendor name, contact, lead time
- **Use count** — track how often each part is used (drives optimization)

---

## Key Features

### Part Management
- Add parts with photo (browsable gallery view)
- Auto-generate part number from description
- Duplicate detection on entry — flag similar existing parts
- Group similar parts near each other in storage

### Location & QR System
- QR code for each part and each bin
- Scan a bin QR to see contents; scan a part QR to see details/location
- Print bin labels to Dymo label printer

### Stock & Reorder
- Track quantity on hand, set minimum threshold per part
- Reorder dashboard — everything below threshold, grouped by supplier
- Adjust quantity on hand directly; downward adjustments increase the part's use count

### Purchase Order Intake
- Photograph/upload a purchase order
- OCR/parse it to identify parts received
- Tell the stocker exactly which bin each part goes to

### Optimize Layout
- Track use count per part
- Suggest optimal placement: high-use parts on lower, easy-access shelves; low-use parts in less accessible areas
- Generate a reorganization plan when triggered

---

## Pages

- `/` — Dashboard: low-stock alerts, recent activity, optimization suggestions
- `/parts` — Searchable list + gallery view with photos
- `/parts/<id>` — Detail: photo, location, stock history, reorder info
- `/parts/new` — Add part (with duplicate check)
- `/bins` — All bins/locations, printable QR labels
- `/reorder` — Items below threshold, grouped by supplier
- `/optimize` — Layout optimization suggestions
- `/intake` — Upload purchase order photo, get stocking instructions

---

## Tech Stack

- Flask + SQLite + SQLAlchemy
- Jinja2 templates + lightweight CSS (Pico or Bootstrap)
- QR code generation (python-qrcode)
- OCR for purchase orders (Tesseract or cloud vision API)
- Dymo label printer integration (DYMO SDK or direct label formatting)

---

## Build Priority

1. Parts CRUD + photo + auto part number
2. Bins/locations + search/filter
3. Stock tracking + reorder alerts
4. QR code generation + Dymo printing
5. Duplicate detection + similar part grouping
6. Purchase order intake (OCR)
7. Usage-based layout optimization
