from ws.base import BaseConsumer, TargetsEnum, Action, Message, auth, BasePayload


class NotificationsConsumer(BaseConsumer):
    broadcast_group = 'notifications'

    @auth
    def connect(self):
        super(NotificationsConsumer, self).connect()

    def post_created_notification(self, event):
        def action_for_target(message: Message, payload: BasePayload):
            return Action(event='post_created_notification', system=event['system'], params=payload.to_data())

        self.send_broadcast(event, action_for_target=action_for_target, target=TargetsEnum.for_all)

    def new_message_notification(self, event):
        def action_for_target(message: Message, payload: BasePayload):
            return Action(event='new_message_notification', system=event['system'], params=payload.to_data())

        self.send_broadcast(event, action_for_target=action_for_target, target=TargetsEnum.for_user)
