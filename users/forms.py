from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


# Create your forms here.

class RegisterForm(UserCreationForm):
    username = forms.CharField(
        max_length=36,
        required=True,
        widget=forms.TextInput(
            attrs={
                "type":"text",
                "class":"form-control",
                "id":"username",
                "placeholder":"Username",
            }
        ),
    )
    email = forms.CharField(
        max_length=36,
        required=False,
        widget=forms.TextInput(
            attrs={
                "type":"text",
                "class":"form-control",
                "id":"email",
                "placeholder":"Email",
            }
        ),
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "type":"password",
                "class":"form-control", 
                "id":"password1", 
                "placeholder":"Password",
            }
        ),
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "type":"password",
                "class":"form-control", 
                "id":"password2", 
                "placeholder":"Confirm Password",
            }
        ),
    )
    


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=36,
        required=True,
        widget=forms.TextInput(
            attrs={
                "type":"text",
                "class":"form-control",
                "id":"username",
                "placeholder":"Username",
            }
        ),
    )

    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "type":"password",
                "class":"form-control", 
                "id":"password", 
                "placeholder":"Password",
            }
        ),
    )