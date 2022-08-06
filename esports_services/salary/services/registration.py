from django.contrib.auth.models import Group, User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import login
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.http import HttpRequest, Http404
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.forms import ModelForm
from django.shortcuts import get_object_or_404

from salary.models import Profile


class TokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for confirmation email.
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"


account_activation_token = TokenGenerator()


def get_confirmation_message(user: User, 
                             request: HttpRequest = None) -> EmailMessage:
    """
    Returns EmailMessage instance with confirmation link
    """
    mail_template = 'salary/auth/confirmation_email.html'
    token_genertor = account_activation_token
    current_site = get_current_site(request)

    email_address = user.email
    mail_subject = 'Активация Вашей учетной записи.'
    message = render_to_string(mail_template, {
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'user': user,
        'token': token_genertor.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http',
    })

    return EmailMessage(mail_subject, message, to=[email_address])


def sending_confirmation_link(request: HttpRequest, username: str) -> None:
    """
    Sending message to user email with confirmation link
    """

    user = get_object_or_404(User, username=username)
    confirm_message = get_confirmation_message(user, request=request)
    confirm_message.send()
    user.profile.email_status = Profile.EmailStatus.SENT
    user.save()


def registration_user(request: HttpRequest,
                      user_form: ModelForm,
                      profile_form: ModelForm) -> User:
    """Performs the procedure for registering an employee in the system

    Returns:
        User: Registred User model instance
    """

    user = user_form.save(commit=False)
    profile = profile_form.save(commit=False)

    user.is_active = False
    for field in ('first_name', 'last_name'):
        field_value = getattr(user, field)
        setattr(user, field, field_value.strip().capitalize())

    user.save()
    profile.user = user

    # Полномочия убираем и даем после подтверждения
    user.groups.add(Group.objects.get(name='employee'))
    if profile.position.name == 'cash_admin':
        user.groups.add(Group.objects.get(name='cashiers'))

    activation_message = get_confirmation_message(user, request=request)
    activation_message.send()

    profile.profile_status = Profile.ProfileStatus.REGISTRED
    profile.email_status = Profile.EmailStatus.SENT
    user.save()

    return user


def get_user_instance_from_uidb64(uidb64_str: str) -> User:
    """
    Decode user pk from unicode string and returning User instance
    """

    uid = urlsafe_base64_decode(uidb64_str).decode()
    return get_object_or_404(User, pk=uid)


def confirmation_user_email(request: HttpRequest,
                            user_uidb64_str: str,
                            request_token: str) -> None:
    """
    Change statuses user email and profile, and call login function
    """

    requested_user = get_user_instance_from_uidb64(uidb64_str=user_uidb64_str)
    is_verified_token = account_activation_token.check_token(
        requested_user, request_token
    )
    if is_verified_token:
        requested_user.is_active = True
        requested_user.profile.email_status = Profile.EmailStatus.CONFIRMED
        requested_user.profile.profile_status = Profile.ProfileStatus.WAIT
        requested_user.save()
        login(request, requested_user)
    else:
        raise Http404
