import random
from datetime import datetime, timedelta, timezone

from faker import Faker

from app import create_app, db
from app.models import (
    Address,
    Category,
    Order,
    OrderItem,
    Product,
    ReturnRequest,
    Shipment,
    User,
)

fake = Faker()
Faker.seed(42)
random.seed(42)

PASSWORD = "test1234"
NOW = datetime.now(timezone.utc)
ORDERS_PER_USER = 18

CATEGORIES = {
    "RPG": "Role-playing games",
    "Racing": "Racing games",
    "Platformer": "Platform games",
    "Action": "Action games",
    "Fighting": "Fighting games",
    "Puzzle": "Puzzle games",
    "Sports": "Sports games",
    "Adventure": "Adventure games",
}

BRANDS = {
    "NES": "Nintendo",
    "SNES": "Nintendo",
    "Game Boy": "Nintendo",
    "N64": "Nintendo",
    "Genesis": "Sega",
    "Dreamcast": "Sega",
    "PS1": "Sony",
    "PS2": "Sony",
}

# (name, genre, console, price)
GAMES = [
    ("Final Fantasy VI", "RPG", "SNES", 44.99),
    ("Chrono Trigger", "RPG", "SNES", 59.99),
    ("EarthBound", "RPG", "SNES", 79.99),
    ("Pokémon Red", "RPG", "Game Boy", 39.99),
    ("Final Fantasy VII", "RPG", "PS1", 29.99),
    ("Phantasy Star IV", "RPG", "Genesis", 49.99),
    ("Super Mario Kart", "Racing", "SNES", 34.99),
    ("Mario Kart 64", "Racing", "N64", 39.99),
    ("F-Zero X", "Racing", "N64", 29.99),
    ("Gran Turismo 2", "Racing", "PS1", 19.99),
    ("Crazy Taxi", "Racing", "Dreamcast", 24.99),
    ("Ridge Racer Type 4", "Racing", "PS1", 24.99),
    ("Super Mario World", "Platformer", "SNES", 39.99),
    ("Sonic the Hedgehog 2", "Platformer", "Genesis", 24.99),
    ("Donkey Kong Country", "Platformer", "SNES", 29.99),
    ("Super Mario 64", "Platformer", "N64", 44.99),
    ("Crash Bandicoot", "Platformer", "PS1", 19.99),
    ("Kirby's Dream Land", "Platformer", "Game Boy", 19.99),
    ("Mega Man X", "Action", "SNES", 49.99),
    ("Metal Gear Solid", "Action", "PS1", 24.99),
    ("Streets of Rage 2", "Action", "Genesis", 29.99),
    ("Contra", "Action", "NES", 34.99),
    ("Ninja Gaiden", "Action", "NES", 29.99),
    ("Devil May Cry", "Action", "PS2", 19.99),
    ("Super Street Fighter II", "Fighting", "SNES", 34.99),
    ("Mortal Kombat II", "Fighting", "Genesis", 24.99),
    ("Tekken 3", "Fighting", "PS1", 19.99),
    ("Soulcalibur", "Fighting", "Dreamcast", 29.99),
    ("Super Smash Bros.", "Fighting", "N64", 49.99),
    ("Tetris", "Puzzle", "Game Boy", 14.99),
    ("Dr. Mario", "Puzzle", "NES", 17.99),
    ("Tetris Attack", "Puzzle", "SNES", 29.99),
    ("Lemmings", "Puzzle", "SNES", 19.99),
    ("Pokémon Puzzle League", "Puzzle", "N64", 34.99),
    ("FIFA 98: Road to World Cup", "Sports", "PS1", 14.99),
    ("NBA Jam", "Sports", "Genesis", 24.99),
    ("Tony Hawk's Pro Skater 2", "Sports", "PS1", 24.99),
    ("Mario Golf", "Sports", "N64", 29.99),
    ("Pro Evolution Soccer 2", "Sports", "PS2", 14.99),
    ("The Legend of Zelda: A Link to the Past", "Adventure", "SNES", 44.99),
    ("The Legend of Zelda: Ocarina of Time", "Adventure", "N64", 49.99),
    ("The Legend of Zelda: Link's Awakening", "Adventure", "Game Boy", 34.99),
    ("Super Metroid", "Adventure", "SNES", 54.99),
    ("Shenmue", "Adventure", "Dreamcast", 24.99),
    ("Resident Evil 2", "Adventure", "PS1", 29.99),
]

# (name, product_type, console, price)
HARDWARE = [
    ("Super Nintendo Console", "console", "SNES", 149.99),
    ("Sega Genesis Console", "console", "Genesis", 129.99),
    ("PlayStation Console", "console", "PS1", 119.99),
    ("Game Boy Classic Console", "console", "Game Boy", 99.99),
    ("SNES Controller", "accessory", "SNES", 24.99),
    ("Genesis 6-Button Controller", "accessory", "Genesis", 22.99),
    ("PS1 Memory Card", "accessory", "PS1", 14.99),
    ("N64 Rumble Pak", "accessory", "N64", 17.99),
    ("Game Boy Link Cable", "accessory", "Game Boy", 9.99),
]

# peak = how many months ago this user bought the most (0 = current month)
CUSTOMERS = [
    {"name": "Ana Pérez", "email": "ana@example.com", "prefs": ["RPG", "Adventure"], "peak": 2},
    {"name": "Bruno Gómez", "email": "bruno@example.com", "prefs": ["Racing", "Sports"], "peak": 5},
    {"name": "Carla Díaz", "email": "carla@example.com", "prefs": ["Platformer", "Puzzle"], "peak": 1},
]

LOCATIONS = [
    ("3400", "Corrientes", "Corrientes"),
    ("3500", "Resistencia", "Chaco"),
    ("3300", "Posadas", "Misiones"),
]
STREETS = ["San Martín", "Belgrano", "Mitre", "Córdoba", "Junín", "Salta"]
CARRIERS = ["Andreani", "OCA", "Correo Argentino"]
RETURN_REASONS = [
    "Disc arrived scratched",
    "Cartridge doesn't save progress",
    "Wrong console version",
    "Box arrived damaged",
]


def month_start(offset):
    year, month = NOW.year, NOW.month - offset
    while month < 1:
        month += 12
        year -= 1
    return datetime(year, month, 1, tzinfo=timezone.utc)


def random_date_in_month(offset):
    start = month_start(offset)
    end = NOW if offset == 0 else month_start(offset - 1)
    seconds = max(int((end - start).total_seconds()), 1)
    return start + timedelta(seconds=random.randint(0, seconds - 1))


def make_product(name, product_type, console, price, category_id=None):
    discount = random.choice([0, 0, 0, 0, 10, 15, 20, 30])
    stock = random.randint(0, 25)
    return Product(
        name=name,
        description=f"{name} ({console})",
        original_price=price,
        price=round(price * (1 - discount / 100), 2),
        discount_percentage=discount,
        stock=stock,
        low_stock=stock <= 5,
        brand=BRANDS[console],
        console=console,
        product_type=product_type,
        active=True,
        category_id=category_id,
    )


def pick_product(prefs, games, games_by_genre, hardware):
    r = random.random()
    if r < 0.10:
        return random.choice(hardware)
    if r < 0.70:
        return random.choice(games_by_genre[random.choice(prefs)])
    return random.choice(games)


def make_order(user, prefs, created, games, games_by_genre, hardware):
    order = Order(user=user, address=user.address, order_date=created, total=0)

    wanted = random.randint(1, 3)
    chosen = {}
    while len(chosen) < wanted:
        product = pick_product(prefs, games, games_by_genre, hardware)
        chosen[product.id] = product

    total = 0
    for product in chosen.values():
        qty = random.choices([1, 2], weights=[80, 20])[0]
        subtotal = round(product.price * qty, 2)
        order.items.append(
            OrderItem(product=product, quantity=qty, unit_price=product.price, subtotal=subtotal)
        )
        total += subtotal
    order.total = round(total, 2)

    age_days = (NOW - created).days
    if age_days > 21:
        order.status = "cancelled" if random.random() < 0.08 else "delivered"
    else:
        order.status = random.choices(["pending", "shipped", "delivered"], weights=[30, 40, 30])[0]

    if order.status in ("shipped", "delivered"):
        order.shipment = Shipment(
            carrier=random.choice(CARRIERS),
            tracking_code=fake.bothify("??#########AR").upper(),
            status="delivered" if order.status == "delivered" else "in_transit",
            estimated_delivery=(created + timedelta(days=random.randint(3, 7))).date(),
        )
    return order


def seed():
    db.drop_all()
    db.create_all()

    categories = {name: Category(name=name, description=desc) for name, desc in CATEGORIES.items()}
    db.session.add_all(categories.values())
    db.session.flush()

    games, hardware = [], []
    games_by_genre = {name: [] for name in categories}
    for name, genre, console, price in GAMES:
        product = make_product(name, "game", console, price, categories[genre].id)
        games.append(product)
        games_by_genre[genre].append(product)
    for name, product_type, console, price in HARDWARE:
        hardware.append(make_product(name, product_type, console, price))
    db.session.add_all(games + hardware)
    db.session.flush()

    admin = User(name="Admin", email="admin@example.com", role="admin")
    admin.set_password(PASSWORD)
    db.session.add(admin)

    delivered_old = []
    for cfg, (postal, city, province) in zip(CUSTOMERS, LOCATIONS):
        address = Address(
            postal_code=postal,
            street=f"{random.choice(STREETS)} {random.randint(100, 3500)}",
            province=province,
            city=city,
        )
        user = User(
            name=cfg["name"],
            email=cfg["email"],
            role="customer",
            phone=fake.bothify("+54 379 4######"),
            address=address,
        )
        user.set_password(PASSWORD)
        db.session.add(user)

        for _ in range(ORDERS_PER_USER):
            offset = cfg["peak"] if random.random() < 0.4 else random.randint(0, 11)
            created = random_date_in_month(offset)
            order = make_order(user, cfg["prefs"], created, games, games_by_genre, hardware)
            db.session.add(order)
            if order.status == "delivered" and (NOW - created).days > 14:
                delivered_old.append((order, created))

    for order, created in random.sample(delivered_old, min(3, len(delivered_old))):
        db.session.add(
            ReturnRequest(
                order=order,
                reason=random.choice(RETURN_REASONS),
                status="pending",
                created_at=created + timedelta(days=10),
            )
        )

    db.session.commit()

    print(
        f"Seed OK: {User.query.count()} users, {Product.query.count()} products, "
        f"{Order.query.count()} orders, {OrderItem.query.count()} items, "
        f"{Shipment.query.count()} shipments, {ReturnRequest.query.count()} returns"
    )
    print(f"Customers: {', '.join(c['email'] for c in CUSTOMERS)} | admin@example.com | password: {PASSWORD}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()