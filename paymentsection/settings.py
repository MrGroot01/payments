from pathlib import Path
import os

# ───────────────────────────────────────────────
# BASE DIR
# ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ───────────────────────────────────────────────
# SECURITY
# ───────────────────────────────────────────────
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-secret-key")

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".onrender.com",
]

# ───────────────────────────────────────────────
# RAZORPAY KEYS
# ───────────────────────────────────────────────
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

# ───────────────────────────────────────────────
# APPLICATIONS
# ───────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    "corsheaders",
    "rest_framework",

    # Local
    "payments",
]

# ───────────────────────────────────────────────
# MIDDLEWARE
# ───────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',

    # ⚠️ Keep CSRF disabled for APIs
    # 'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ───────────────────────────────────────────────
# CORS SETTINGS (VERY IMPORTANT)
# ───────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://ecomerce-website-gold.vercel.app",
]

CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
]

CORS_ALLOW_CREDENTIALS = True

# ───────────────────────────────────────────────
# REST FRAMEWORK (REMOVE AUTH ISSUE ✅)
# ───────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny"
    ],
     "DEFAULT_AUTHENTICATION_CLASSES": []
}

# ───────────────────────────────────────────────
# URLS
# ───────────────────────────────────────────────
ROOT_URLCONF = 'paymentsection.urls'

# ───────────────────────────────────────────────
# TEMPLATES
# ───────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'paymentsection.wsgi.application'

# ───────────────────────────────────────────────
# DATABASE
# ───────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ───────────────────────────────────────────────
# PASSWORD VALIDATION
# ───────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ───────────────────────────────────────────────
# INTERNATIONALIZATION
# ───────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ───────────────────────────────────────────────
# STATIC FILES
# ───────────────────────────────────────────────
STATIC_URL = 'static/'

# ───────────────────────────────────────────────
# LOGGING
# ───────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}