import os

from salary.models import Profile


def profile_photo_is_exists(profile: Profile) -> bool:
    """
    Return True if profile.photo is defined and image file is exists.
    """
    if profile.photo and os.path.exists(profile.photo.path):
        return True
    
    return False
