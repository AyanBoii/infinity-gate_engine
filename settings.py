# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings for API access
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True 