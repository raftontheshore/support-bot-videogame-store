from app import create_app
from app.models import User
from app.services import purchases_by_month, top_genres

app = create_app()
with app.app_context():
    for user in User.query.filter_by(role="customer"):
        print(user.name)
        print("  top months:", purchases_by_month(user.id)[:3])
        print("  top genres:", top_genres(user.id, 3))