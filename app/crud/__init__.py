from app.crud.user import (
    authenticate_user,
    create_user,
    delete_user,
    get_user,
    get_user_by_email,
    update_user,
)
from app.crud.post import (
    count_posts,
    create_post,
    delete_post,
    get_post,
    get_posts,
    update_post,
)
from app.crud.comment import (
    create_comment,
    delete_comment,
    get_comment,
    get_comments_by_post,
    update_comment,
)
from app.crud.tag import attach_tags_to_post, get_or_create_tag

__all__ = [
    # user
    "authenticate_user",
    "create_user",
    "get_user",
    "get_user_by_email",
    "update_user",
    "delete_user",
    # post
    "count_posts",
    "create_post",
    "get_post",
    "get_posts",
    "update_post",
    "delete_post",
    # comment
    "create_comment",
    "get_comment",
    "get_comments_by_post",
    "update_comment",
    "delete_comment",
    # tag
    "get_or_create_tag",
    "attach_tags_to_post",
]
