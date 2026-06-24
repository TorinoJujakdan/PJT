from django.conf import settings
from django.db import models


class CommunityPost(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="community_posts",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=120)
    content = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} by {self.author_id}"


class CommunityPostBookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="community_post_bookmarks",
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        CommunityPost,
        related_name="bookmarks",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_community_post_bookmark",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="community_c_user_id_96b901_idx"),
            models.Index(fields=["post", "-created_at"], name="community_c_post_id_50d05f_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} bookmarked {self.post_id}"
