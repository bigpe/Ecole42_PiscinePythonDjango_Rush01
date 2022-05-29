from django import forms
from django.contrib.auth import authenticate

from django.contrib.auth import get_user_model

from forum.models import Post

User = get_user_model()


class SignUpForm(forms.Form):
    username = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        if User.objects.filter(username=self.cleaned_data.get('username')):
            raise forms.ValidationError("UsernameView already exist.")
        if self.cleaned_data.get('password') != self.cleaned_data.get('password_confirm'):
            raise forms.ValidationError("Passwords don't match.")
        return self.cleaned_data


class SignInForm(forms.Form):
    username = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    user_cache = None

    def clean(self):
        try:
            username = User.objects.get(username=self.cleaned_data['username']).username
        except User.DoesNotExist:
            raise forms.ValidationError("No such user registered.")

        self.user_cache = authenticate(username=username, password=self.cleaned_data['password'])
        if self.user_cache is None or not self.user_cache.is_active:
            raise forms.ValidationError("UsernameView or password is incorrect.")
        return self.cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'description', 'profile_picture']


class ProfileDetailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'description']

    def __init__(self, *args, **kwargs):
        super(ProfileDetailForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            for field in instance._meta.fields:
                if field.name in self.fields:
                    self.fields[field.name].widget.attrs['readonly'] = True


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ['author', 'vote_up', 'vote_down']
