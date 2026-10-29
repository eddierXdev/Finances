"""SQLAlchemy settings repository."""

from sqlalchemy.orm import Session

from app.infrastructure.database.models import SettingModel
from app.infrastructure.database.timestamp import utc_now


class SqlAlchemySettingsRepository:
    """Persist simple key/value application settings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, key: str) -> str | None:
        model = self._session.get(SettingModel, key)
        return model.value if model is not None else None

    def set(self, key: str, value: str) -> None:
        model = self._session.get(SettingModel, key)
        if model is None:
            self._session.add(
                SettingModel(
                    key=key,
                    value=value,
                    updated_at=utc_now(),
                )
            )
        else:
            model.value = value
            model.updated_at = utc_now()
        self._session.flush()
