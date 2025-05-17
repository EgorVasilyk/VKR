from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm, PasswordChangeForm
from .models import *


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Введите почту'
        })
        self.fields['username'].widget.attrs.update({
            'type': 'text',
            'id': 'username',
            'name': 'username',
            'minlength': '4',
            'maxlength': '30',
            'class': 'form-input',
        })
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'id': 'password1',
            'name': 'password1',
            'pattern': '(?=.*\d)(?=.*[a-zA-Z]).{4,}',
            'title': 'Пароль должен содержать минимум 4 символов, включая цифры и буквы',
            'class': 'form-input'
        }
        )
        self.fields['password2'].widget.attrs.update({
            'id': 'password2',
            'name': 'password2',
            'class': 'form-input'
        }
        )

    class Meta:
        model = Users
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Users.objects.filter(email=email).exists():
            raise forms.ValidationError("Эта почта уже используется.")
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Введите логин'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Введите пароль'
        })

    error_messages = {
        'invalid_login': "Неправильный логин или пароль.",
        'inactive': "Этот аккаунт неактивен.",
    }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Настройка полей с ограничениями
        self.fields['old_password'].widget = forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Текущий пароль',
            'autocomplete': 'current-password'
        })

        self.fields['new_password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Новый пароль',
            'pattern': '(?=.*\d)(?=.*[a-zA-Z]).{4,}',
            'title': 'Пароль должен содержать минимум 4 символа, включая цифры и буквы',
            'autocomplete': 'new-password',
            'minlength': '4'
        })

        self.fields['new_password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Подтвердите новый пароль',
            'autocomplete': 'new-password'
        })

    error_messages = {
        'password_incorrect': "Текущий пароль введен неверно.",
        'password_mismatch': "Пароли не совпадают.",
        'password_too_short': "Пароль должен содержать минимум 4 символа.",
        'password_no_digit': "Пароль должен содержать хотя бы одну цифру.",
        'password_no_letter': "Пароль должен содержать хотя бы одну букву.",
    }

    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')

        if len(password1) < 4:
            raise forms.ValidationError(
                self.error_messages['password_too_short'],
                code='password_too_short',
            )

        if not any(char.isdigit() for char in password1):
            raise forms.ValidationError(
                self.error_messages['password_no_digit'],
                code='password_no_digit',
            )

        if not any(char.isalpha() for char in password1):
            raise forms.ValidationError(
                self.error_messages['password_no_letter'],
                code='password_no_letter',
            )

        return password1


class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        label="Новый email",
        widget=forms.EmailInput(attrs={'class': 'form-input'})
    )

    def clean_new_email(self):
        email = self.cleaned_data.get('new_email')
        if Users.objects.filter(email=email).exists():
            raise forms.ValidationError("Этот email уже используется.")
        return email


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goals
        fields = ['title', 'type', 'start_date', 'end_date', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class GoalItemForm(forms.ModelForm):
    class Meta:
        model = GoalItems
        fields = ['title', 'description', 'deadline', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'deadline': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }


class UserEditForm(UserChangeForm):
    class Meta:
        model = Users
        fields = ['username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('password', None)
        self.fields['username'].widget.attrs.update({'class': 'form-input'})
