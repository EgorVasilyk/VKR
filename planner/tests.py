from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from planner.forms import RegistrationForm, LoginForm
from planner.models import Roles

User = get_user_model()

# Общие настройки для тестов
TEST_SETTINGS = {
    'AUTHENTICATION_BACKENDS': ['django.contrib.auth.backends.ModelBackend'],
    'PASSWORD_HASHERS': ['django.contrib.auth.hashers.MD5PasswordHasher'],
}


class AuthFormsTests(TestCase):
    """Тесты форм с доступом к БД"""

    @classmethod
    def setUpTestData(cls):
        # Создаем тестовую роль
        cls.role = Roles.objects.create(name='client')

    def test_registration_form_valid(self):
        form = RegistrationForm(data={
            'username': 'testuser',
            'password1': 'TestPass123',
            'password2': 'TestPass123'
        })
        self.assertTrue(form.is_valid())

    def test_login_form_valid(self):
        # Сначала создаем пользователя
        User.objects.create_user(
            username='testuser',
            password='TestPass123',
            role=self.role
        )

        form = LoginForm(data={
            'username': 'testuser',
            'password': 'TestPass123'
        })
        self.assertTrue(form.is_valid())


@override_settings(**TEST_SETTINGS)
class AuthViewsTests(TestCase):
    """Тесты представлений"""

    @classmethod
    def setUpTestData(cls):
        cls.role = Roles.objects.create(name='client')
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=cls.role
        )

    def test_successful_login(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('calendar'))

    def test_registration_flow(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'NewPass123',
            'password2': 'NewPass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('calendar'))
        self.assertTrue(User.objects.filter(username='newuser').exists())


class UserModelTests(TestCase):
    """Тесты модели пользователя"""

    def setUp(self):
        self.role = Roles.objects.create(name='testrole')

    def test_user_creation(self):
        user = User.objects.create_user(
            username='modeluser',
            password='testpass123',
            role=self.role
        )
        self.assertEqual(user.role.name, 'testrole')
        self.assertEqual(user.groups.count(), 0)

    def test_user_str(self):
        user = User.objects.create_user(
            username='struser',
            password='testpass123',
            role=self.role
        )
        self.assertEqual(str(user), 'struser')


class TemplateTests(TestCase):
    """Тесты шаблонов"""

    def test_login_template(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'Авторизация')
        self.assertTemplateUsed(response, 'planner/login.html')

    def test_register_template(self):
        response = self.client.get(reverse('register'))
        self.assertContains(response, 'Регистрация')
        self.assertTemplateUsed(response, 'planner/register.html')