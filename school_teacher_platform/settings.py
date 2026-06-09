from pathlib import Path
import environ
from django.utils.translation import gettext_lazy as _

# ------------------------------------------------------------
# Base directory
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------
# Environment setup
# ------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    CORS_ALLOW_ALL_ORIGINS=(bool, True),
)

environ.Env.read_env(BASE_DIR / ".env")

# ------------------------------------------------------------
# Core Django settings
# ------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="django-insecure-school-teacher-platform-secret-key-2024")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# ------------------------------------------------------------
# Applications
# ------------------------------------------------------------
INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.inlines',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',

    'schools',
    'teachers',
    'recommender',
]

# ------------------------------------------------------------
# Middleware
# ------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'school_teacher_platform.urls'

# ------------------------------------------------------------
# Templates
# ------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'school_teacher_platform.wsgi.application'

# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': env("DB_ENGINE"),
        'NAME': BASE_DIR / env("DB_NAME") if "sqlite3" in env("DB_ENGINE") else env("DB_NAME"),
        'USER': env("DB_USER", default=""),
        'PASSWORD': env("DB_PASSWORD", default=""),
        'HOST': env("DB_HOST", default=""),
        'PORT': env("DB_PORT", default=""),
    }
}

# ------------------------------------------------------------
# Password validation
# ------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------
LANGUAGE_CODE = env("LANGUAGE_CODE", default="en")

TIME_ZONE = env("TIME_ZONE", default="Asia/Tehran")

USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('en', _('English')),
    ('fa', _('Persian')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ------------------------------------------------------------
# Static files
# ------------------------------------------------------------
STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------------------------------------------------
# Django REST Framework
# ------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL_ORIGINS")

# ------------------------------------------------------------
# Unfold Admin configuration
# ------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": _("School-Teacher Platform"),
    "SITE_HEADER": _("School-Teacher Platform"),
    "SITE_SUBHEADER": _("Matching schools with the right teachers"),
    "SITE_URL": "/",
    "SITE_ICON": {
        "light": None,
        "dark": None,
    },
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "6px",
    "COLORS": {
        "font": {
            "subtle-light": "107 114 128",
            "subtle-dark": "156 163 175",
            "default-light": "75 85 99",
            "default-dark": "209 213 219",
            "important-light": "17 24 39",
            "important-dark": "243 244 246",
        },
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Schools"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Schools"),
                        "icon": "school",
                        "link": "/admin/schools/school/",
                        "permission": lambda request: request.user.has_perm("schools.view_school"),
                    },
                    {
                        "title": _("Subject needs"),
                        "icon": "book",
                        "link": "/admin/schools/subjectneed/",
                        "permission": lambda request: request.user.has_perm("schools.view_subjectneed"),
                    },
                ],
            },
            {
                "title": _("Teachers"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Teachers"),
                        "icon": "person",
                        "link": "/admin/teachers/teacher/",
                        "permission": lambda request: request.user.has_perm("teachers.view_teacher"),
                    },
                    {
                        "title": _("Teaching subjects"),
                        "icon": "menu_book",
                        "link": "/admin/teachers/teachingsubject/",
                        "permission": lambda request: request.user.has_perm("teachers.view_teachingsubject"),
                    },
                ],
            },
            {
                "title": _("Recommender"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Matches"),
                        "icon": "handshake",
                        "link": "/admin/recommender/teacherschoolmatch/",
                        "permission": lambda request: request.user.has_perm("recommender.view_teacherschoolmatch"),
                    },
                ],
            },
            {
                "title": _("Administration"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "manage_accounts",
                        "link": "/admin/auth/user/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": "/admin/auth/group/",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
        ],
    },
}