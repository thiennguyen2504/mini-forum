from sqlalchemy.orm import Session

from app.models.post import Post
from app.models.tag import Tag


def get_or_create_tag(db: Session, name: str) -> Tag:
    """
    Trả về Tag đã có hoặc tạo mới nếu chưa tồn tại.

    Lưu ý: hàm này KHÔNG commit — để transaction cha quyết định.
    Điều này đảm bảo tag không bao giờ được persist độc lập ngoài
    transaction của attach_tags_to_post.
    """
    tag = db.query(Tag).filter(Tag.name == name).first()
    if tag is None:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()  # flush để lấy id, nhưng chưa commit
    return tag


def attach_tags_to_post(db: Session, post_id: int, tag_names: list[str]) -> Post:
    """
    Gắn danh sách tag vào bài viết trong một transaction duy nhất.

    - Với mỗi tên tag: gọi get_or_create_tag (flush, chưa commit).
    - Gắn tất cả tag vào post.tags.
    - Commit toàn bộ một lần — tag và liên kết cùng được ghi hoặc cùng rollback.
    - Nếu xảy ra lỗi bất kỳ: rollback() và raise lại exception gốc
      để đảm bảo không có tag mồ côi.

    Raises:
        LookupError: Nếu post_id không tồn tại.
        Exception: Bất kỳ lỗi DB nào trong quá trình flush/commit.
    """
    post = db.get(Post, post_id)
    if post is None:
        raise LookupError(f"Post id={post_id} not found.")

    try:
        tags: list[Tag] = []
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            tag = get_or_create_tag(db, name)
            tags.append(tag)

        # Thay toàn bộ tag list (idempotent: set lại chứ không append thêm)
        post.tags = tags

        db.commit()
        db.refresh(post)
    except Exception:
        db.rollback()
        raise

    return post
