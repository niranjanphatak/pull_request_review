# Quick Start: Switching Database Backends

This guide helps you quickly switch between MongoDB and DynamoDB in the PR Review System.

## TL;DR

**Use MongoDB** (easiest for local development):
```bash
echo "DATABASE_TYPE=mongodb" >> .env
```

**Use DynamoDB** (best for AWS deployments):
```bash
echo "DATABASE_TYPE=dynamodb" >> .env
python scripts/setup_dynamodb_tables.py
```

## Step-by-Step Instructions

### Option 1: MongoDB (Recommended for Local Development)

**1. Install MongoDB**

macOS:
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

Ubuntu/Debian:
```bash
sudo apt-get install mongodb
sudo systemctl start mongodb
```

Docker:
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

**2. Configure Environment**

Create or edit `.env`:
```bash
DATABASE_TYPE=mongodb
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=pr_review
```

**3. Start Application**
```bash
python server.py
```

That's it! MongoDB will automatically create the necessary collections.

---

### Option 2: DynamoDB (Recommended for AWS Production)

**1. Set Up AWS Credentials**

Install AWS CLI:
```bash
# macOS
brew install awscli

# Ubuntu/Debian
sudo apt-get install awscli
```

Configure credentials:
```bash
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Output format (json)
```

**2. Configure Environment**

Create or edit `.env`:
```bash
DATABASE_TYPE=dynamodb
DYNAMODB_REGION=us-east-1
DYNAMODB_TABLE_PREFIX=pr_review
```

**3. Create DynamoDB Tables**
```bash
python scripts/setup_dynamodb_tables.py
```

You should see:
```
✅ Created table: pr_review_sessions
✅ Created table: pr_review_snapshots
✅ Created table: pr_review_prompts
✅ Created table: pr_review_onboarding
✅ All tables created successfully!
```

**4. Start Application**
```bash
python server.py
```

---

## Switching Databases

### From MongoDB to DynamoDB

1. Stop your application
2. Update `.env`:
   ```bash
   DATABASE_TYPE=dynamodb
   ```
3. Set up DynamoDB:
   ```bash
   python scripts/setup_dynamodb_tables.py
   ```
4. Restart application

### From DynamoDB to MongoDB

1. Stop your application
2. Update `.env`:
   ```bash
   DATABASE_TYPE=mongodb
   ```
3. Ensure MongoDB is running
4. Restart application

---

## Verify Database Connection

Check the health endpoint:
```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "ok",
  "database_type": "mongodb",
  "database_status": "connected"
}
```

or for DynamoDB:
```json
{
  "status": "ok",
  "database_type": "dynamodb",
  "database_status": "connected"
}
```

---

## Common Issues

### MongoDB: "Connection refused"
**Problem**: MongoDB is not running

**Solution**:
```bash
# Check if MongoDB is running
mongosh --eval "db.adminCommand('ping')"

# If not, start it:
# macOS:
brew services start mongodb-community

# Linux:
sudo systemctl start mongodb

# Docker:
docker start mongodb
```

### DynamoDB: "Unable to locate credentials"
**Problem**: AWS credentials not configured

**Solution**:
```bash
# Option 1: Configure AWS CLI
aws configure

# Option 2: Set environment variables in .env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### DynamoDB: "Table does not exist"
**Problem**: Tables not created

**Solution**:
```bash
python scripts/setup_dynamodb_tables.py
```

---

## Using Local DynamoDB (for Development)

If you want to use DynamoDB locally without AWS:

**1. Install DynamoDB Local**
```bash
docker run -d -p 8000:8000 --name dynamodb-local \
  amazon/dynamodb-local
```

**2. Configure for Local**

Update `.env`:
```bash
DATABASE_TYPE=dynamodb
DYNAMODB_REGION=us-east-1
DYNAMODB_ENDPOINT_URL=http://localhost:8000
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
```

**3. Create Tables**
```bash
python scripts/setup_dynamodb_tables.py
```

---

## Production Recommendations

### For Small to Medium Projects
- **Use MongoDB Atlas** (free tier available)
- Easy to set up
- No AWS account needed
- Good query performance

### For AWS-Based Infrastructure
- **Use DynamoDB**
- Seamless AWS integration
- Serverless (auto-scaling)
- Pay only for what you use
- Consider on-demand billing mode

### Cost Comparison

**MongoDB Atlas (Free Tier)**:
- 512 MB storage
- Shared cluster
- Good for development/small apps

**DynamoDB (Free Tier)**:
- 25 GB storage
- 25 RCU/WCU included
- Good for most applications

---

## Need Help?

- Full documentation: See [DATABASE_SETUP.md](DATABASE_SETUP.md)
- Environment variables: See [.env.example](.env.example)
- Issues: Check application logs and database connectivity

## Next Steps

After setting up your database:
1. Configure your AI API keys in `.env`
2. Set up GitHub token for private repositories
3. Start reviewing pull requests!

Happy coding!
