from django.core.cache import cache
from django.utils import timezone

__all__ = ['is_cache_token_left']


def is_cache_token_left(token_id: str, token_max_cnt: int, token_duration: timezone.timedelta) -> bool:
    token = cache.get(token_id)
    if token is None:
        token_cnt = token_max_cnt
        token_cooldown = timezone.now() + token_duration
    else:
        token_cnt, token_cooldown = token
        if token_cooldown < timezone.now():
            token_cnt = token_max_cnt
            token_cooldown = timezone.now() + token_duration

    if token_cnt <= 0:
        return False
    token_cnt -= 1

    cache.set(token_id, (token_cnt, token_cooldown), token_duration.total_seconds())

    return True
