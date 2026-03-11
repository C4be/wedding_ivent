import logging
from typing import AsyncGenerator, List

from fastapi import Depends

from repositories.posts_repository import PostsRepository, get_posts_repository
from schemas.post_schema import PreparedPostCreate, PreparedPostUpdate
from database.models import PreparedPost



class PostsService:
    def __init__(self, repo: PostsRepository):
        self.repo = repo

    async def create_post(self, data: PreparedPostCreate) -> PreparedPost:
        logging.info("Creating post with parse_mode=%s, text_length=%d", data.parse_mode, len(data.text))
        post = await self.repo.create_post(data)
        logging.info("Post created: id=%s", post.id)
        return post

    async def get_post(self, post_id: int) -> PreparedPost:
        logging.info("Fetching post: id=%s", post_id)
        post = await self.repo.get_post(post_id)
        if post is None:
            logging.warning("Post not found: id=%s", post_id)
            raise ValueError(f"Post with id={post_id} not found")
        logging.info("Post found: id=%s", post_id)
        return post

    async def get_all_posts(self) -> List[PreparedPost]:
        logging.info("Fetching all posts")
        posts = await self.repo.get_all_posts()
        logging.info("Fetched %d posts", len(posts))
        return posts

    async def update_post(self, post_id: int, data: PreparedPostUpdate) -> PreparedPost:
        logging.info("Updating post: id=%s, fields=%s", post_id, data.model_dump(exclude_unset=True))
        post = await self.repo.update_post(post_id, data)
        if post is None:
            logging.warning("Post not found for update: id=%s", post_id)
            raise ValueError(f"Post with id={post_id} not found")
        logging.info("Post updated: id=%s", post_id)
        return post

    async def delete_post(self, post_id: int) -> bool:
        logging.info("Deleting post: id=%s", post_id)
        deleted = await self.repo.delete_post(post_id)
        if not deleted:
            logging.warning("Post not found for deletion: id=%s", post_id)
            raise ValueError(f"Post with id={post_id} not found")
        logging.info("Post deleted: id=%s", post_id)
        return True


async def get_posts_service(
    repo: PostsRepository = Depends(get_posts_repository),
) -> AsyncGenerator[PostsService, None]:
    yield PostsService(repo)
