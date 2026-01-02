"""
Database Factory - Creates appropriate database instance based on configuration
"""
from config import Config
from utils.database_interface import DatabaseInterface


def create_database() -> DatabaseInterface:
    """
    Create and return the appropriate database instance based on configuration

    Returns:
        DatabaseInterface: MongoDB or DynamoDB storage instance
    """
    db_type = Config.get_database_type()

    if db_type == 'mongodb':
        from utils.session_storage import SessionStorage
        return SessionStorage()
    elif db_type == 'dynamodb':
        from utils.dynamodb_storage import DynamoDBStorage
        dynamodb_config = Config.get_dynamodb_config()
        return DynamoDBStorage(**dynamodb_config)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def get_database_info() -> dict:
    """
    Get information about the current database configuration

    Returns:
        dict: Database type and connection status
    """
    db_type = Config.get_database_type()

    return {
        'type': db_type,
        'mongodb_uri': Config.MONGODB_URI if db_type == 'mongodb' else None,
        'mongodb_db_name': Config.MONGODB_DB_NAME if db_type == 'mongodb' else None,
        'dynamodb_region': Config.DYNAMODB_REGION if db_type == 'dynamodb' else None,
        'dynamodb_table_prefix': Config.DYNAMODB_TABLE_PREFIX if db_type == 'dynamodb' else None,
    }
