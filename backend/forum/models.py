from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    description = models.CharField(max_length=300, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures', null=True, blank=True)

    # notifications: Notification
    # messages: Message
    # posts: Post

    @property
    def reputation(self):
        rep = 0
        posts = self.posts.all()
        for post in posts:
            rep += post.vote_up.count() * 5
            rep -= post.vote_down.count() * 2
        return rep

    @property
    def forum_notification(self):
        return Notification.objects.filter(type='forum', is_read=False, user=self).all()

    @property
    def message_notification(self):
        return Notification.objects.filter(type='message', is_read=False, user=self).all()


class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    vote_up = models.ManyToManyField(User, related_name='vote_up')
    vote_down = models.ManyToManyField(User, related_name='vote_down')
    author = models.ForeignKey(User, models.CASCADE, related_name='posts')

    # comments: Comment

    class Meta:
        ordering = ['-date']


@receiver(post_save, sender=Post)
def post_notification(instance, created, **kwargs):
    if not created:
        return

    from ws.base import get_system_cache, ActionSystem
    for user in User.objects.all():
        Notification.objects.create(user=user, content=instance.title, type='forum')

    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        'notifications',
        {'type': 'post.created.notification',
         'params': {'title': instance.title[:30]},
         'system': ActionSystem(**get_system_cache(instance.author)).to_data()}
    )


class Comment(models.Model):
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    post = models.ForeignKey(Post, models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, models.CASCADE)


class Notification(models.Model):
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    type = models.CharField(max_length=50)
    user = models.ForeignKey(User, models.CASCADE, related_name='notifications')


class Chat(models.Model):
    author = models.ForeignKey(User, models.CASCADE, related_name='chat_message_author')
    recipient = models.ForeignKey(User, models.CASCADE, related_name='chat_message_recipient')
    # chat_messages: Message


class Message(models.Model):
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, models.CASCADE, related_name='messages')
    recipient = models.ForeignKey(User, models.CASCADE, related_name='recipient')
    chat = models.ForeignKey(Chat, models.CASCADE, null=True, blank=True, related_name='chat_messages')


@receiver(post_save, sender=Message)
def message_notification(instance, created, **kwargs):
    if not created:
        return
    from ws.base import get_system_cache, ActionSystem

    Notification.objects.create(user=instance.recipient, content=instance.content, type='message')
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        'notification',
        {'type': 'new.message.notification',
         'params': {'content': instance.content[:30], 'author': instance.author.username,
                    'to_user_id': instance.recipient.id},
         'system': ActionSystem(**get_system_cache(instance.author)).to_data()}
    )
    if not instance.chat:
        if not Chat.objects.filter(author=instance.author, recipient=instance.recipient):
            instance.chat = Chat.objects.create(author=instance.author, recipient=instance.recipient)
        elif not Chat.objects.filter(recipient=instance.author, author=instance.recipient):
            instance.chat = Chat.objects.create(author=instance.author, recipient=instance.recipient)
        else:
            chat = Chat.objects.filter(author=instance.author, recipient=instance.recipient).first()
            chat_reverse = Chat.objects.filter(author=instance.recipient, recipient=instance.author).first()
            if chat:
                instance.chat = chat
            else:
                instance.chat = chat_reverse
