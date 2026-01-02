# Database Setup Guide

The PR Review System supports two database backends:
- **MongoDB** (default)
- **DynamoDB** (AWS)

You can switch between them with a simple configuration change.

## Quick Start

### Using MongoDB (Default)

1. Install MongoDB locally or use a MongoDB service
2. Set environment variables in `.env`:
```bash
DATABASE_TYPE=mongodb
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=pr_review
```

3. Start MongoDB:
```bash
# macOS (Homebrew)
brew services start mongodb-community

# Linux (systemd)
sudo systemctl start mongod

# Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

4. MongoDB will automatically create collections on first use

### Using DynamoDB

1. Set up AWS credentials (choose one method):

   **Option A: Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   ```

   **Option B: AWS CLI Configuration**
   ```bash
   aws configure
   ```

   **Option C: IAM Role** (if running on EC2/ECS/Lambda)
   - No credentials needed, uses instance role

2. Configure database settings in `.env`:
```bash
DATABASE_TYPE=dynamodb
DYNAMODB_REGION=us-east-1
DYNAMODB_TABLE_PREFIX=pr_review
# Optional: Set if not using default AWS credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

3. Create DynamoDB tables:
```bash
python scripts/setup_dynamodb_tables.py
```

4. Start your application - it will now use DynamoDB

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_TYPE` | `mongodb` | Database to use: `mongodb` or `dynamodb` |

#### MongoDB Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | `mongodb://localhost:27017/` | MongoDB connection string |
| `MONGODB_DB_NAME` | `pr_review` | Database name |

#### DynamoDB Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DYNAMODB_REGION` | `us-east-1` | AWS region |
| `DYNAMODB_TABLE_PREFIX` | `pr_review` | Prefix for table names |
| `AWS_ACCESS_KEY_ID` | - | AWS access key (optional) |
| `AWS_SECRET_ACCESS_KEY` | - | AWS secret key (optional) |
| `DYNAMODB_ENDPOINT_URL` | - | Custom endpoint (for local DynamoDB) |

## Switching Databases

To switch from MongoDB to DynamoDB:

1. Update `.env`:
```bash
# Change this line
DATABASE_TYPE=mongodb
# To this
DATABASE_TYPE=dynamodb
```

2. Set up DynamoDB (if not already done):
```bash
python scripts/setup_dynamodb_tables.py
```

3. Restart your application:
```bash
# Kill the running process and restart
python server.py
```

To switch back to MongoDB:

1. Update `.env`:
```bash
DATABASE_TYPE=mongodb
```

2. Restart your application

## Database Schema

Both databases store the same data with identical structure:

### Collections/Tables

1. **sessions** - PR review sessions and results
2. **statistics_snapshots** - Historical statistics snapshots
3. **prompt_versions** - AI prompt version tracking
4. **onboarding** - Team and repository onboarding data

### Key Differences

| Feature | MongoDB | DynamoDB |
|---------|---------|----------|
| ID Field | `_id` (ObjectId) | `session_id` (UUID) |
| Queries | Rich queries & aggregations | Scan with filters |
| Indexing | Automatic on `_id` | GSI for timestamp |
| TTL | Field: `timestamp` | Field: `ttl` (auto-delete) |
| Local Dev | Easy with Docker | Requires DynamoDB Local |

## Local Development

### MongoDB with Docker
```bash
# Start MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest

# View logs
docker logs mongodb

# Stop MongoDB
docker stop mongodb
```

### DynamoDB Local
```bash
# Start DynamoDB Local
docker run -d -p 8000:8000 --name dynamodb \
  amazon/dynamodb-local

# Configure for local DynamoDB
export DYNAMODB_ENDPOINT_URL=http://localhost:8000

# Create tables
python scripts/setup_dynamodb_tables.py

# Stop DynamoDB Local
docker stop dynamodb
```

## Production Considerations

### MongoDB Production

1. **Atlas (Recommended)**:
   - Create free cluster at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
   - Get connection string
   - Update `MONGODB_URI` with Atlas connection string

2. **Self-Hosted**:
   - Enable authentication
   - Use replica sets for high availability
   - Regular backups
   - Monitor disk usage

### DynamoDB Production

1. **Capacity Planning**:
   - Default: 5 RCU / 5 WCU per table (provisioned)
   - Consider on-demand billing for variable workloads
   - Monitor CloudWatch metrics

2. **Cost Optimization**:
   - Enable TTL to auto-delete old records
   - Use on-demand pricing for unpredictable traffic
   - Set up CloudWatch alarms for throttling

3. **Security**:
   - Use IAM roles instead of access keys
   - Enable encryption at rest
   - VPC endpoints for private access
   - Enable point-in-time recovery

4. **Scaling**:
   - Auto-scaling for provisioned capacity
   - Or use on-demand mode (recommended)
   - Monitor throttled requests

## Migrating Data

### MongoDB to DynamoDB

```python
# migration_mongo_to_dynamodb.py
from utils.session_storage import SessionStorage
from utils.dynamodb_storage import DynamoDBStorage
from config import Config

# Connect to both databases
mongo_db = SessionStorage()
dynamo_db = DynamoDBStorage(**Config.get_dynamodb_config())

# Migrate sessions
sessions = mongo_db.get_recent_sessions(limit=1000)
for session in sessions:
    # Remove MongoDB _id
    if '_id' in session:
        del session['_id']
    dynamo_db.save_session(session)

print(f"Migrated {len(sessions)} sessions")
```

### DynamoDB to MongoDB

```python
# migration_dynamodb_to_mongo.py
from utils.session_storage import SessionStorage
from utils.dynamodb_storage import DynamoDBStorage
from config import Config

# Connect to both databases
dynamo_db = DynamoDBStorage(**Config.get_dynamodb_config())
mongo_db = SessionStorage()

# Migrate sessions
sessions = dynamo_db.get_recent_sessions(limit=1000)
for session in sessions:
    # Remove DynamoDB session_id, let MongoDB generate _id
    if 'session_id' in session:
        del session['session_id']
    mongo_db.save_session(session)

print(f"Migrated {len(sessions)} sessions")
```

## Troubleshooting

### MongoDB Connection Issues

**Problem**: `MongoDB not available: ServerSelectionTimeoutError`

**Solutions**:
- Check if MongoDB is running: `mongosh --eval "db.adminCommand('ping')"`
- Verify connection string in `MONGODB_URI`
- Check firewall/network settings
- For Atlas: Check IP whitelist

### DynamoDB Connection Issues

**Problem**: `DynamoDB not available: NoCredentialsError`

**Solutions**:
- Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- Or configure AWS CLI: `aws configure`
- Verify credentials: `aws sts get-caller-identity`

**Problem**: `ResourceNotFoundException: Requested resource not found`

**Solutions**:
- Run table creation script: `python scripts/setup_dynamodb_tables.py`
- Verify table prefix matches `DYNAMODB_TABLE_PREFIX`
- Check region matches `DYNAMODB_REGION`

**Problem**: `AccessDeniedException`

**Solutions**:
- Verify IAM permissions include:
  - `dynamodb:CreateTable`
  - `dynamodb:PutItem`
  - `dynamodb:GetItem`
  - `dynamodb:Query`
  - `dynamodb:Scan`
  - `dynamodb:UpdateItem`
  - `dynamodb:DeleteItem`

### Performance Issues

**MongoDB**:
- Create indexes on frequently queried fields
- Use aggregation pipelines efficiently
- Monitor slow queries

**DynamoDB**:
- Use batch operations for multiple items
- Avoid full table scans, use indexes
- Monitor provisioned capacity
- Consider switching to on-demand mode

## Health Check

Check database connectivity via the health endpoint:

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "ok",
  "database_type": "mongodb",
  "database_status": "connected"
}
```

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify environment variables are set correctly
3. Test database connectivity independently
4. Review this documentation for troubleshooting steps

## Advanced Configuration

### Custom Table Names (DynamoDB)

Set a different prefix for all tables:
```bash
DYNAMODB_TABLE_PREFIX=myapp_prod
```

This creates tables:
- `myapp_prod_sessions`
- `myapp_prod_snapshots`
- `myapp_prod_prompts`
- `myapp_prod_onboarding`

### Multiple Environments

Use different `.env` files:

```bash
# .env.development
DATABASE_TYPE=mongodb
MONGODB_URI=mongodb://localhost:27017/

# .env.production
DATABASE_TYPE=dynamodb
DYNAMODB_REGION=us-east-1
DYNAMODB_TABLE_PREFIX=pr_review_prod
```

Load the appropriate file:
```bash
# Development
cp .env.development .env

# Production
cp .env.production .env
```
