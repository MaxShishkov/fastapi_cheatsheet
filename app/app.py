from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.schemas import PostCreate, PostResponse, UserRead, UserCreate, UserUpdate
from app.db import Post, create_db_and_tables, get_async_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select

text_posts = {"1": {"title": "First Post", "content": "This is the first post."},
              "2": {"title": "Second Post", "content": "This is the second post."},
              "3": {"title": "Third Post", "content": "This is the third post."}}

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/") # ?limit=2
async def home(limit: int = None):
    if limit:
        return list(text_posts.values())[:limit]
    return text_posts

@app.post("/posts/{id}")
async def get_post(id: str):
    if id not in text_posts:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post = text_posts.get(id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@app.post("/posts")
def create_post(post: PostCreate) -> PostResponse:
    new_id = str([max(text_posts.keys())] + 1)
    text_posts[new_id] = {"title": post.title, "content": post.content}
    return {"id": new_id, "title": post.title, "content": post.content}

@app.post("/upload")
async def upload_file(
        file: UploadFile = File(...),
        caption: str = Form(""),
        user: User = Depends(current_active_user),
        session: AsyncSession = Depends(get_async_session)
):
    new_post = Post(
        user_id=user.id,
        caption=caption,
        url=f"/files/{file.filename}",
        file_type=file.content_type,
        file_name=file.filename
    )
    session.add(new_post)
    await session.commit()
    await session.refresh(new_post)
    return {"id": new_post.id, "url": new_post.url, "caption": new_post.caption}

@app.get("/feed")
async def get_feed(
        session: AsyncSession = Depends(get_async_session),
        user: User = Depends(current_active_user),
):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]

    result = await session.execute(select(User))
    users = [row[0] for row in result.all()]
    user_dict = {u.id: u.email for u in users}

    posts_data = []
    for post in posts:
        posts_data.append(
            {
                "id": str(post.id),
                "user_id": str(post.user_id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": post.created_at.isoformat(),
                "is_owner": post.user_id == user.id,
                "email": user_dict.get(post.user_id, "Unknown")
            }
        )

    return {"posts": posts_data}
