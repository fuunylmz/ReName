from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.media import AppSetting
from app.schemas.media import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = SettingsRead().model_dump()


@router.get("", response_model=SettingsRead)
def read_settings(session: Session = Depends(get_session)) -> SettingsRead:
    values = DEFAULT_SETTINGS.copy()
    rows = session.exec(select(AppSetting)).all()
    for row in rows:
        values[row.key] = row.value
    return SettingsRead(**values)


@router.put("", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate, session: Session = Depends(get_session)) -> SettingsRead:
    values = payload.model_dump()
    for key, value in values.items():
        setting = session.get(AppSetting, key)
        if setting:
            setting.value = value
        else:
            setting = AppSetting(key=key, value=value)
        session.add(setting)
    session.commit()
    return read_settings(session)


@router.get("/{key}")
def read_setting(key: str, session: Session = Depends(get_session)) -> dict[str, object]:
    setting = session.get(AppSetting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="配置不存在")
    return {"key": key, "value": setting.value}
