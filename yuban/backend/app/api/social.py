"""社区 API"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_db
from app.models import Post, PostType, User, Spot
from app.schemas import PostCreate, PostOut

router = APIRouter()


@router.get("/feed", response_model=list[PostOut])
async def feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    post_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """动态广场 Feed"""
    stmt = select(Post).order_by(desc(Post.created_at))

    if post_type:
        try:
            stmt = stmt.where(Post.type == PostType(post_type))
        except ValueError:
            pass

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    posts = result.scalars().all()

    out = []
    for p in posts:
        d = PostOut.model_validate(p)
        if p.user:
            d.user = {"id": p.user.id, "nickname": p.user.nickname, "avatar": p.user.avatar}
        if p.spot:
            d.spot = {"id": p.spot.id, "name": p.spot.name}
        out.append(d)
    return out


@router.post("/posts", response_model=PostOut)
async def create_post(
    data: PostCreate,
    db: AsyncSession = Depends(get_db),
):
    """发布动态（MVP阶段使用固定用户ID=1）"""
    # TODO: 接入微信登录后从token获取真实user_id
    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(openid="dev_user", nickname="测试钓友", avatar="")
        db.add(user)
        await db.flush()

    post = Post(
        user_id=user.id,
        spot_id=data.spot_id,
        type=PostType(data.type),
        content=data.content,
        images=data.images,
        fish_info=data.fish_info,
        lat=data.lat,
        lng=data.lng,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    d = PostOut.model_validate(post)
    d.user = {"id": user.id, "nickname": user.nickname, "avatar": user.avatar}
    return d


@router.get("/posts/{post_id}", response_model=PostOut)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    d = PostOut.model_validate(post)
    if post.user:
        d.user = {"id": post.user.id, "nickname": post.user.nickname, "avatar": post.user.avatar}
    if post.spot:
        d.spot = {"id": post.spot.id, "name": post.spot.name}
    return d
