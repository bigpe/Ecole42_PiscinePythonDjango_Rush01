from ws.base import BaseConsumer, TargetsEnum, Action, Message, auth, BasePayload


class ChatConsumer(BaseConsumer):
    broadcast_group = 'chat'

    @auth
    def connect(self):
        super(ChatConsumer, self).connect()

    def message_send(self, event):
        def action_for_target(message: Message, payload: BasePayload):
            return Action(event='message_show', system=event['system'], params=payload.to_data())

        self.send_broadcast(event, action_for_target=action_for_target, target=TargetsEnum.for_user)
