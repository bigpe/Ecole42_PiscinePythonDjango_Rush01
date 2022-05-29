from django.contrib.auth.models import AbstractUser
from django.db import models


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

    def save(self, *args, **kwargs):
        for user in User.objects.all():
            Notification.objects.create(user=user, content=self.title, type='forum')
        super(Post, self).save(*args, **kwargs)


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

    def save(self, *args, **kwargs):
        Notification.objects.create(user=self.recipient, content=self.content, type='message')
        if not self.chat:
            if not Chat.objects.filter(author=self.author, recipient=self.recipient):
                self.chat = Chat.objects.create(author=self.author, recipient=self.recipient)
            elif not Chat.objects.filter(recipient=self.author, author=self.recipient):
                self.chat = Chat.objects.create(author=self.author, recipient=self.recipient)
            else:
                chat = Chat.objects.filter(author=self.author, recipient=self.recipient).first()
                chat_reverse = Chat.objects.filter(author=self.recipient, recipient=self.author).first()
                if chat:
                    self.chat = chat
                else:
                    self.chat = chat_reverse

        super(Message, self).save(*args, **kwargs)
