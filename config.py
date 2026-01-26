import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration settings for the PR Review application"""

    # AI Configuration
    AI_API_KEY = os.getenv('AI_API_KEY')
    AI_BASE_URL = os.getenv('AI_BASE_URL')
    AI_MODEL = os.getenv('AI_MODEL')
    AI_TEMPERATURE = os.getenv('AI_TEMPERATURE')
    AI_ANALYSIS_TEMPERATURE = os.getenv('AI_ANALYSIS_TEMPERATURE')

    # Database Configuration
    DATABASE_TYPE = os.getenv('DATABASE_TYPE')

    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME')

    # DynamoDB Configuration
    DYNAMODB_REGION = os.getenv('DYNAMODB_REGION')
    DYNAMODB_TABLE_PREFIX = os.getenv('DYNAMODB_TABLE_PREFIX')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    DYNAMODB_ENDPOINT_URL = os.getenv('DYNAMODB_ENDPOINT_URL')

    # GitHub Configuration
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

    # Repository Configuration
    TEMP_REPO_DIR = os.getenv('TEMP_REPO_DIR')

    # Review Settings
    MAX_FILE_SIZE = os.getenv('MAX_FILE_SIZE')
    _SUPPORTED_EXTENSIONS_STR = os.getenv('SUPPORTED_EXTENSIONS')
    SUPPORTED_EXTENSIONS = _SUPPORTED_EXTENSIONS_STR.split(',') if _SUPPORTED_EXTENSIONS_STR else []

    # Logging Configuration
    LOG_FILE = os.getenv('LOG_FILE')

    @classmethod
    def get_ai_api_key(cls):
        """Get AI API key"""
        return cls.AI_API_KEY

    @classmethod
    def get_ai_model(cls):
        """Get AI model"""
        return cls.AI_MODEL

    @classmethod
    def get_ai_temperature(cls):
        """Get AI temperature"""
        return float(cls.AI_TEMPERATURE) if cls.AI_TEMPERATURE else None

    @classmethod
    def get_ai_base_url(cls):
        """Get AI base URL (returns None for default)"""
        return cls.AI_BASE_URL

    @classmethod
    def get_ai_analysis_temperature(cls):
        """Get AI analysis temperature (for code quality analysis)"""
        return float(cls.AI_ANALYSIS_TEMPERATURE) if cls.AI_ANALYSIS_TEMPERATURE else None

    @classmethod
    def get_database_type(cls):
        """Get database type (mongodb or dynamodb)"""
        return cls.DATABASE_TYPE.lower() if cls.DATABASE_TYPE else None

    @classmethod
    def get_mongodb_uri(cls):
        """Get MongoDB connection URI"""
        return cls.MONGODB_URI

    @classmethod
    def get_mongodb_db_name(cls):
        """Get MongoDB database name"""
        return cls.MONGODB_DB_NAME

    @classmethod
    def get_dynamodb_config(cls):
        """Get DynamoDB configuration"""
        config = {
            'region_name': cls.DYNAMODB_REGION,
            'table_prefix': cls.DYNAMODB_TABLE_PREFIX
        }
        if cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY:
            config['aws_access_key_id'] = cls.AWS_ACCESS_KEY_ID
            config['aws_secret_access_key'] = cls.AWS_SECRET_ACCESS_KEY
        if cls.DYNAMODB_ENDPOINT_URL:
            config['endpoint_url'] = cls.DYNAMODB_ENDPOINT_URL
        return config

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.AI_API_KEY:
            raise ValueError("AI_API_KEY is required")

        db_type = cls.get_database_type()
        if db_type == 'mongodb':
            if not cls.MONGODB_URI:
                raise ValueError("MONGODB_URI is required when DATABASE_TYPE is 'mongodb'")
        elif db_type == 'dynamodb':
            if not cls.DYNAMODB_REGION:
                raise ValueError("DYNAMODB_REGION is required when DATABASE_TYPE is 'dynamodb'")
        else:
            raise ValueError(f"Invalid DATABASE_TYPE: {db_type}. Must be 'mongodb' or 'dynamodb'")

    @classmethod
    def get_config_dict(cls):
        """Get configuration as dictionary"""
        return {
            'ai_api_key': cls.get_ai_api_key(),
            'ai_model': cls.get_ai_model(),
            'ai_temperature': cls.get_ai_temperature(),
            'ai_base_url': cls.get_ai_base_url(),
            'temp_repo_dir': cls.TEMP_REPO_DIR,
            'max_file_size': int(cls.MAX_FILE_SIZE) if cls.MAX_FILE_SIZE else None,
            'supported_extensions': cls.SUPPORTED_EXTENSIONS
        }
