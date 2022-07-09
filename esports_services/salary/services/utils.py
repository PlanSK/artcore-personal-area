from django.utils.text import slugify


def get_chat_slug(type: str, id: int) -> str:
    if type == 'DIALOG':
        return slugify(f'dialog_id{id}')
    else:
        return slugify(f'chat_id{id}')
