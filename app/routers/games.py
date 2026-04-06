from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.game import Game, GamePlatform
from app.models.platform import Platform
from app.models.user import UserRole
from app.schemas.game import GameCreate, GameUpdate, GameResponse
from app.dependencies import require_role

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("", response_model=list[GameResponse])
async def list_games(
    platform_id: int | None = Query(default=None),
    year: int | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Game).options(
        selectinload(Game.platforms).selectinload(GamePlatform.platform)
    )

    if platform_id:
        query = query.join(GamePlatform).where(GamePlatform.platform_id == platform_id)
    if year:
        query = query.where(Game.release_year == year)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(game_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Game)
        .options(selectinload(Game.platforms).selectinload(GamePlatform.platform))
        .where(Game.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("", response_model=GameResponse, status_code=201)
async def create_game(
    payload: GameCreate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role(UserRole.admin)),
):

    game = Game(
        title=payload.title,
        description=payload.description,
        release_year=payload.release_year,
        cover_image_url=payload.cover_image_url,
    )
    db.add(game)
    await db.flush()  # get game.id before committing

    for platform_id in payload.platform_ids:
        db.add(GamePlatform(game_id=game.id, platform_id=platform_id))

    await db.commit()
    result = await db.execute(
        select(Game)
        .options(selectinload(Game.platforms).selectinload(GamePlatform.platform))
        .where(Game.id == game.id)
    )
    return result.scalar_one()


@router.put("/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: int,
    payload: GameUpdate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(
        select(Game)
        .options(selectinload(Game.platforms).selectinload(GamePlatform.platform))
        .where(Game.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if payload.title is not None:
        game.title = payload.title
    if payload.description is not None:
        game.description = payload.description
    if payload.release_year is not None:
        game.release_year = payload.release_year
    if payload.cover_image_url is not None:
        game.cover_image_url = payload.cover_image_url

    if payload.platform_ids is not None:
        await db.execute(
            GamePlatform.__table__.delete().where(GamePlatform.game_id == game_id)
        )
        for platform_id in payload.platform_ids:
            db.add(GamePlatform(game_id=game.id, platform_id=platform_id))

    await db.commit()
    result = await db.execute(
        select(Game)
        .options(selectinload(Game.platforms).selectinload(GamePlatform.platform))
        .where(Game.id == game_id)
    )
    return result.scalar_one()


@router.delete("/{game_id}", status_code=204)
async def delete_game(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    await db.execute(
        GamePlatform.__table__.delete().where(GamePlatform.game_id == game_id)
    )
    await db.delete(game)
    await db.commit()
