from django.conf import settings
from django.db import models


class CommunityPost(models.Model):
    station = models.ForeignKey(
        "stations.GasStation",
        related_name="community_posts",
        on_delete=models.CASCADE,
    )
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
            models.Index(fields=["station", "-created_at"]),
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} by {self.author_id}"
