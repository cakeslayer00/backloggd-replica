import csv
import io
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.celery_app import celery_app
from app.core.config import settings
from app.tasks.email_tasks import send_email_with_attachment


engine = create_engine(
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)
SessionLocal = sessionmaker(bind=engine)


@celery_app.task(bind=True)
def export_user_backlog_to_csv(self, user_id: int, username: str, email: str):
    print(f"[EXPORT] Starting export for user {user_id} ({username})")

    session = SessionLocal()
    try:
        from app.models.user import User
        from app.models.backlog_entry import BacklogEntry
        from app.models.game import Game

        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"[EXPORT] User {user_id} not found")
            return {"error": "User not found"}

        entries = (
            session.query(BacklogEntry, Game)
            .join(Game, BacklogEntry.game_id == Game.id)
            .filter(BacklogEntry.user_id == user_id)
            .order_by(BacklogEntry.created_at.desc())
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Game Title",
                "Status",
                "Priority",
                "Hours Played",
                "Added to Backlog",
                "Last Updated",
            ]
        )

        for entry, game in entries:
            writer.writerow(
                [
                    game.title,
                    entry.status.value,
                    entry.priority.value,
                    entry.hours_played or 0,
                    entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    entry.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(entry, "updated_at")
                    else "",
                ]
            )

        csv_content = output.getvalue()
        csv_size = len(csv_content)
        print(
            f"[EXPORT] Generated CSV with {len(entries)} entries, size: {csv_size / 1024:.2f} KB"
        )

        filename = f"backlog_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        send_email_with_attachment(
            to_email=email,
            subject=f"Your BacklogGD Export - {len(entries)} games",
            body=f"Hi {username},\n\nYour backlog export is ready. You have {len(entries)} games in your backlog.\n\nBest,\nThe BacklogGD Team",
            filename=filename,
            content=csv_content,
        )

        print(f"[EXPORT] Email sent to {email}")

        output.seek(0)
        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "entry_count": len(entries),
            "csv_size_bytes": csv_size,
        }

    finally:
        session.close()


