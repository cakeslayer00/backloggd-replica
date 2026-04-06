from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.review import Review
from app.models.game import Game
from app.models.user import User, UserRole
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewResponse])
async def list_reviews(
    game_id: int | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Review)
    if game_id:
        query = query.where(Review.game_id == game_id)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("", response_model=ReviewResponse, status_code=201)
async def create_review(
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Game).where(Game.id == payload.game_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Game not found")

    result = await db.execute(
        select(Review).where(
            Review.user_id == current_user.id,
            Review.game_id == payload.game_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already reviewed this game")

    review = Review(
        user_id=current_user.id,
        game_id=payload.game_id,
        score=payload.score,
        body=payload.body,
        is_spoiler=payload.is_spoiler,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    payload: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    is_owner = review.user_id == current_user.id
    is_moderator = current_user.role in (UserRole.moderator, UserRole.admin)

    if not is_owner and not is_moderator:
        raise HTTPException(status_code=403, detail="Not allowed to edit this review")

    if payload.score is not None:
        review.score = payload.score
    if payload.body is not None:
        review.body = payload.body
    if payload.is_spoiler is not None:
        review.is_spoiler = payload.is_spoiler

    await db.commit()
    await db.refresh(review)
    return review


@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    is_owner = review.user_id == current_user.id
    is_moderator = current_user.role in (UserRole.moderator, UserRole.admin)

    if not is_owner and not is_moderator:
        raise HTTPException(status_code=403, detail="Not allowed to delete this review")

    await db.delete(review)
    await db.commit()