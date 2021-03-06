"""
Websocket: Base
====================================
Base websocket consumer
"""
import dataclasses
import json
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Any

from asgiref.sync import async_to_sync
from channels.consumer import get_handler_name
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

from .utils import safe

User = get_user_model()


def auth(f):
    def wrapper(self, *args, **kwargs):
        try:
            user = self.get_user()
            if user.is_anonymous:
                self.close()
            self.accept()
            return f(self)
        except Exception:
            ...

    wrapper.__doc__ = f.__doc__
    return wrapper


def check_auth(f):
    def wrapper(self, *args, **kwargs):
        try:
            user = self.get_user()
            if not user.is_anonymous:
                return f(self, *args, **kwargs)
        except Exception:
            ...

    wrapper.__doc__ = f.__doc__
    return wrapper


def check_payload(f):
    @wraps(f)
    def wrapper(self: BaseConsumer, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except AttributeError as e:
            required_payload = str(e).split('attribute')[1].strip().replace("'", '')
            event = {
                'system': self.get_systems().to_data(),
                'params': {}
            }

            def action_for_initiator(message: Message, payload):
                return Action(
                    event=ActionsEnum.error,
                    params=ResponsePayloads.PayloadSignatureWrong(required=required_payload).to_data(),
                    system=self.get_systems()
                )

            self.send_broadcast(event, action_for_initiator=action_for_initiator)

    wrapper.__doc__ = f.__doc__
    return wrapper


def check_recipient(f):
    def wrapper(message: Message, payload: BasePayload, *args, **kwargs):
        if message.target_user:
            return f(message, payload, *args, **kwargs)
        else:
            action = Action(
                event=ActionsEnum.error,
                params=ResponsePayloads.RecipientNotExist().to_data(),
                system=ActionSystem(**message.system.to_data())
            )
            return action

    wrapper.__doc__ = f.__doc__
    return wrapper


def check_recipient_not_me(f):
    def wrapper(message: Message, payload: BasePayload, *args, **kwargs):
        if message.target_user != message.initiator_user:
            return f(message, payload, *args, **kwargs)
        else:
            action = Action(
                event=ActionsEnum.error,
                params=ResponsePayloads.RecipientIsMe().to_data(),
                system=ActionSystem(**message.system.to_data())
            )
            return action

    wrapper.__doc__ = f.__doc__
    return wrapper


class ActionsEnum:
    """List of existed actions"""
    error = 'error'  #: :func:`BaseConsumer.error`


@dataclass
class ActionSystem:
    initiator_channel: str = None  #: Action initiator channel name
    initiator_user_id: int = None  #: Action initiator user id

    def to_data(self):
        return {
            'initiator_channel': self.initiator_channel,
            'initiator_user_id': self.initiator_user_id,
        }


@dataclass
class Action:
    """Action signature for request and response"""
    event: str  #: Action's name
    system: ActionSystem  #: System event information
    params: Any = dataclasses.field(default_factory=dict)  #: Action's params

    def __str__(self, to_json=True):
        data = ActionData(
            type=self.event,
            params=self.params,
            system=self.system
        ).to_data()
        if to_json:
            return json.dumps(data)
        return data

    def to_system_data(self):
        return self.__str__(to_json=False)

    def to_data(self, to_json=False):
        data = {
            'event': self.event,
            'params': self.params,
            'system': self.system.to_data() if isinstance(self.system, ActionSystem) else self.system
        }
        if to_json:
            json.dumps(data, default=lambda o: o.__dict__)
        return data

    def to_json(self):
        return self.to_data(to_json=True)


@dataclass
class ActionData:
    type: str  #: Handler's name
    params: Any  #: Handler's params
    system: ActionSystem  #: System handler information

    def to_data(self):
        return {
            'type': self.type,
            'params': self.params,
            'system': self.system.to_data() if isinstance(self.system, ActionSystem) else self.system
        }


@dataclass
class MessageSystem:
    initiator_channel: str  #: Initiator channel name
    receiver_channel: str  #: Receiver channel name
    initiator_user_id: int  #: Initiator user id

    def to_data(self):
        return {
            'initiator_channel': self.initiator_channel,
            'initiator_user_id': self.initiator_user_id,
        }


class TargetsEnum:
    """Broadcast targets"""
    for_all = 'for_all'  #: For all users in broadcast group
    for_user = 'for_user'  #: For specific user


class Message:
    user: User  #: User who receive message
    system: MessageSystem  #: System message information
    target: TargetsEnum  #: Target for broadcast
    to_user_id: int = None  #: Message target user id
    to_username: str = None  #: Message target user username

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def is_target(self):
        # TODO Add extend lookup logic for child Consumer
        not_initiator = self.system.initiator_channel != self.system.receiver_channel
        if self.target == TargetsEnum.for_all:
            return not_initiator
        if self.target == TargetsEnum.for_user:
            return (self.user.id == self.to_user_id or
                    self.user.username == self.to_username
                    ) and not_initiator
        return False

    @property
    def is_initiator(self):
        return self.system.initiator_channel == self.system.receiver_channel

    @property
    def initiator_user(self) -> User:
        return User.objects.get(id=self.system.initiator_user_id)

    @property
    def target_user(self) -> User:
        # TODO Add extend lookup logic for child Consumer
        if self.to_user_id:
            return User.objects.filter(id=self.to_user_id).first()
        if self.to_username:
            return User.objects.filter(username=self.to_username).first()

    @property
    def before_send_activated(self):
        result = cache.get(self.system.initiator_channel)
        return result

    def before_send_activate(self):
        cache.set(self.system.initiator_channel, True, 180)

    def before_send_drop(self):
        cache.delete(self.system.initiator_channel)


class BasePayload:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        return json.dumps(self.to_data())

    def to_data(self):
        return self.__dict__

    def __repr__(self):
        return self.to_data()


class ResponsePayloads:
    """List of response params signatures"""

    @dataclass
    class ActionNotExist(BasePayload):
        message: str = 'Action not exist'  #: Error message

    @dataclass
    class PayloadSignatureWrong(BasePayload):
        required: str  #: Hint about missing signature
        message: str = 'Payload signature wrong'  #: Error message

    @dataclass
    class ActionSignatureWrong(BasePayload):
        unexpected: str  #: Hint about unexpected signature
        message: str = 'Action signature wrong'  #: Error message

    @dataclass
    class RecipientNotExist(BasePayload):
        message: str = 'Recipient not exist'  #: Error message

    @dataclass
    class RecipientIsMe(BasePayload):
        message: str = 'You cannot be the recipient'  #: Error message

    @dataclass
    class Error(BasePayload):
        message: str  #: Error message


def user_cache_key(user: User):
    return f'user-{user.id}'


def get_system_cache(user: User):
    return cache.get(user_cache_key(user), {})


class BaseConsumer(JsonWebsocketConsumer):
    broadcast_group = None

    def connect(self):
        self.cache_system()
        self.join_group(self.broadcast_group)

    def send_json(self, content, close=False):
        if 'system' in content:
            content.pop('system')
        super(BaseConsumer, self).send_json(content, close)

    def cache_system(self):
        cache.set(user_cache_key(self.get_user()), self.get_systems().to_data(), 40 * 60)

    def get_user(self, user_id: int = None) -> User:
        return User.objects.get(id=user_id) if user_id else self.scope.get('user', AnonymousUser())

    def join_group(self, group_name: str):
        if group_name:
            async_to_sync(self.channel_layer.group_add)(group_name, self.channel_name)

    def leave_group(self, group_name: str):
        if group_name:
            async_to_sync(self.channel_layer.group_discard)(group_name, self.channel_name)

    def get_systems(self) -> ActionSystem:
        return ActionSystem(initiator_channel=self.channel_name, initiator_user_id=self.scope['user'].id)

    @safe
    def receive(self, *arg, **kwargs):
        super().receive(*arg, **kwargs)

    @safe
    def send(self, *arg, **kwargs):
        super().send(*arg, **kwargs)

    def receive_json(self, content, **kwargs):
        if self.broadcast_group:
            try:
                action = Action(**content, system=self.get_systems())
            except TypeError as e:
                unexpected = str(e).split('argument')[1].strip().replace("'", '')
                action = Action(
                    event=ActionsEnum.error,
                    params=ResponsePayloads.ActionSignatureWrong(unexpected=unexpected).to_data(),
                    system=self.get_systems()
                )
                self.send_json(content=action.to_data())
                return
            if action:
                action_handler = getattr(self, get_handler_name(action.to_system_data()), None)
                if not action_handler:
                    action = Action(
                        event=ActionsEnum.error,
                        params=ResponsePayloads.ActionNotExist().to_data(),
                        system=self.get_systems()
                    )
                    self.send_json(content=action.to_data())
                    return
                async_to_sync(self.channel_layer.group_send)(self.broadcast_group, action.to_system_data())

    def send_to_group(self, action: Action, group_name: str = None):
        async_to_sync(
            self.channel_layer.group_send
        )(self.broadcast_group if not group_name else group_name, action.to_system_data())

    @safe
    def send_broadcast(self, event, action_for_target: Callable = None, action_for_initiator: Callable = None,
                       target=TargetsEnum.for_user, before_send: Callable = None, system_before_send: Callable = None):
        payload = BasePayload(**event['params'])
        message = Message(
            **payload.to_data(),
            system=MessageSystem(
                **ActionSystem(**event['system']).to_data(),
                receiver_channel=self.channel_name
            ),
            user=self.scope['user'],
            target=target
        )

        if system_before_send:
            system_before_send()

        if (message.target == TargetsEnum.for_user and not message.target_user) and message.is_initiator:
            action = Action(
                event=ActionsEnum.error,
                params=ResponsePayloads.RecipientNotExist().to_data(),
                system=ActionSystem(**message.system.to_data())
            )
            self.send_json(content=action.to_data())
            return  # Interrupt action for initiator and action for target if recipient not found

        def before():
            if before_send and not message.before_send_activated:
                act: Action = before_send(message, payload)
                if act:
                    self.send_json(content=act.to_data())
                message.before_send_activate()
                return True
            return False

        if message.is_initiator and action_for_initiator:
            activated = before()
            action: Action = action_for_initiator(message, payload)
            if action:
                self.send_json(content=action.to_data())
            if message.before_send_activated and not activated:
                message.before_send_drop()

        if message.is_target and action_for_target:
            activated = before()
            action: Action = action_for_target(message, payload)
            if action:
                self.send_json(content=action.to_data())
            if message.before_send_activated and not activated:
                message.before_send_drop()

    def error(self, event):
        """
        Show error message

        Other Parameters
        -------
        Response Initiator
            :obj:`.Action` :obj:`.ResponsePayloads.Error`
        """

        def action_for_initiator(message: Message, payload: ResponsePayloads.Error):
            return Action(
                event=ActionsEnum.error,
                params=ResponsePayloads.Error(message=payload.message).to_data(),
                system=event['system']
            )

        self.send_broadcast(event, action_for_initiator=action_for_initiator)
