from typing import *
from collections import namedtuple
import logging

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from salary.models import *


Dialog = namedtuple('Dialog', ['member', 'photo', 'unread_messages_count', 'is_selected', 'slug'])

chat_logger = logging.getLogger(__name__)


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
    member=chat.members.exclude(id=user_id).select_related('profile').last()
    unread_messages_count=chat.chat.filter(author=member, is_read=False).count()
    return Dialog(
            member=member,
            photo=member.profile.photo.url if member.profile.photo else None,
            unread_messages_count=unread_messages_count,
            is_selected=is_selected,
            slug=chat.slug,
        )



def get_chats_list(user_id: int, selected_slug: str = '') -> List[Dialog]:
    """Return chats list

    Args:
        user_id (int): user id
        selected_slug (str, optional): slug of the selected chat. Defaults to ''.

    Returns:
        List[Dialog]: list of Dialog
    """
    chats_list = []
    for chat in get_user_chats_list(user_id):
        is_selected = True if selected_slug and selected_slug == chat.slug else False
        chats_list.append(
            get_chat_info(chat, user_id, is_selected)
        )

    return chats_list


def get_messages_list(chat_slug: str) -> QuerySet:
    """Return dialog messages

    Args:
        chat_slug (str): Chat model slug field value

    Returns:
        QuerySet: Message models of the chat
    """

    messages_queryset = Message.objects.filter(
        chat__slug=chat_slug
    ).select_related('author__profile', 'chat').order_by('sending_time')

    return messages_queryset


def get_acvite_users_list(user_id: int) -> QuerySet:
    """Returns users queryset with attribute 'is_active' is True
    """

    active_users_queryset = User.objects.select_related(
        'profile',
    ).exclude(pk=user_id).filter(is_active=True)

    return active_users_queryset


def members_chat_exists(author: User, recipient: User) -> QuerySet:
    """Return queryset with Chats of author and recipient

    Args:
        author (User): author user
        recipient (User): recipient user

    Returns:
        QuerySet: QuerySet of Chats
    """
    chat = (Chat.objects.filter(members=author) & 
            Chat.objects.filter(members=recipient))

    return chat


def get_members_chat(author: User, recipient: User) -> Chat:
    """Return Chat model

    Args:
        author (User): Message author
        recipient (User): Message recipient

    Returns:
        Chat: Chat model
    """
    chat = members_chat_exists(author, recipient)

    if chat and chat.count() == 1:
        if chat.count() > 1:
            chat_logger.warning(f'Duplicate chat detected: {author.username} and {recipient.username}')
        return chat.last()
    else:
        chat = Chat.objects.create()
        chat.members.set((author, recipient))
        chat.save()

    return chat


def add_message_and_return_chat(request: HttpRequest) -> Chat:
    """Add message to chat and return Chat model

    Args:
        request (HttpRequest): Http request with POST attributes

    Raises:
        ValueError: Not enough arguments

    Returns:
        Chat: Chat model
    """
    message_text = request.POST.get('message')
    author = request.user
    recipient = get_object_or_404(User, pk=request.POST.get('recipient_id'))
    chat = get_members_chat(author, recipient)
    if all((message_text, author, recipient, chat)):
        new_message = Message.objects.create(
            chat = chat,
            author = author,
            message_text = message_text
        )
        new_message.save()
    else:
        raise ValueError('Not enough arguments for new message.')

    return chat

def mark_messages_as_read(messages: QuerySet, user: User) -> None:
    """Sets the attribute value to true for messages where the user is not the author

    Args:
        messages (QuerySet): Message QuerySet
        user (User): Recipient of messages
    """
    for message in messages.exclude(author=user).filter(is_read=False):
        message.is_read = True
        message.save()
