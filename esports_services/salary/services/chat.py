from typing import *
from collections import namedtuple

from django.db.models import QuerySet
from salary.models import *


Dialog = namedtuple('Dialog', ['name', 'photo', 'unread_messages_count', 'is_selected', 'slug'])


def get_user_chats_list(user_id: int) -> QuerySet:
    """Return queryset of user chat's

    Args:
        user_id (int): User id

    Returns:
        QuerySet: models.Chat QuerySet
    """

    return User.objects.get(pk=user_id).chat_set.all()


def get_chat_info(chat, user_id: int, is_selected: bool = False) -> Dialog:
    """Return dialog information for user_id interlocutor

    Args:
        chat (QuerySet): Chat
        user_id (int): _description_

    Returns:
        Dialog: named tuple
    """
    if chat.type == 'DIALOG':
        member=chat.members.exclude(id=user_id).last()
        unread_count=chat.chat.filter(author=member, is_read=False).count()
        return Dialog(
                name=member.get_full_name(),
                photo=member.profile.photo if member.profile.photo else None,
                unread_messages_count=unread_count if unread_count else 0,
                is_selected=is_selected,
                slug=chat.slug,
            )
    else:
        pass


def get_chats_list(user_id: int, selected_slug: str = '') -> List[Dialog]:
    """Return dialogs list

    Args:
        user_id (int): user id
        selected_slug (str, optional): slug of the selected chat. Defaults to ''.

    Returns:
        List[Dialog]: list of Dialog
    """
    dialogs_list = []
    for chat in get_user_chats_list(user_id):
        is_selected = True if selected_slug and selected_slug == chat.slug else False
        dialogs_list.append(
            get_chat_info(chat, user_id, is_selected)
        )

    return dialogs_list


def get_messages_list(chat_slug: str) -> QuerySet:
    """Return dialog messages

    Args:
        chat_slug (str): Chat model slug field value

    Returns:
        QuerySet: Message models of the chat
    """

    messages_queryset = Message.objects.filter(
        chat__slug=chat_slug
    ).select_related('author__profile').order_by('sending_time')

    return messages_queryset


def get_acvite_users_list() -> QuerySet:
    """Returns users queryset with attribute 'is_active' is True
    """

    active_users_queryset = User.objects.filter(
        is_active=True
    ).select_related('profile')

    return active_users_queryset
