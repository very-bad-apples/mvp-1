"""
DynamoDB configuration and connection management using PynamoDB.
"""

from pynamodb.connection import Connection
from pynamodb.models import Model
from config import settings
import structlog

logger = structlog.get_logger()


class BaseDynamoModel(Model):
    """
    Base model for all DynamoDB models with common configuration.
    
    Note: Credentials are NOT set here. Child models (like MVProjectItem) 
    set credentials in their Meta class only for local DynamoDB.
    For production, PynamoDB uses boto3's credential chain (env vars, IAM roles).
    """

    class Meta:
        region = settings.DYNAMODB_REGION
        # Credentials are set in child model Meta classes for local DynamoDB only


def init_dynamodb_tables() -> None:
    """
    Initialize DynamoDB tables for the application.
    Creates tables if they don't exist.
    
    This function is idempotent and safe to call multiple times.
    Handles race conditions where table creation might be attempted concurrently.
    """
    from mv_models import MVProjectItem
    from pynamodb.exceptions import TableError

    try:
        # Try to check if table exists, but handle timeout gracefully
        try:
            table_exists = MVProjectItem.exists()
        except TableError as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                logger.warning(
                    "dynamodb_exists_check_timeout",
                    message="Table existence check timed out, attempting to create table anyway",
                    error=str(e)
                )
                table_exists = False
            else:
                raise

        if not table_exists:
            logger.info("dynamodb_table_creating", table_name=settings.DYNAMODB_TABLE_NAME)
            try:
                MVProjectItem.create_table(
                    read_capacity_units=5,
                    write_capacity_units=5,
                    wait=True
                )
                logger.info("dynamodb_table_created", table_name=settings.DYNAMODB_TABLE_NAME)
            except TableError as e:
                # Check if table already exists (can happen in race conditions)
                error_str = str(e).lower()
                if "already exists" in error_str or "resourceinuseexception" in error_str or "table already exists" in error_str:
                    logger.info("dynamodb_table_exists", table_name=settings.DYNAMODB_TABLE_NAME)
                else:
                    raise
        else:
            logger.info("dynamodb_table_exists", table_name=settings.DYNAMODB_TABLE_NAME)
    except Exception as e:
        logger.error("dynamodb_table_init_error", error=str(e), exc_info=True)
        raise

