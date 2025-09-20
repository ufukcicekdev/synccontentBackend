# PostgreSQL Setup Guide for SyncContents

## 1. Install PostgreSQL

### On macOS (using Homebrew):
```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Connect to PostgreSQL as superuser
psql postgres
```

### On Ubuntu/Debian:
```bash
# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Connect to PostgreSQL as superuser
sudo -u postgres psql
```

### On Windows:
- Download PostgreSQL from https://www.postgresql.org/download/windows/
- Follow the installation wizard
- Use pgAdmin or command line to connect

## 2. Database Setup

1. **Run the SQL setup script:**
```bash
# Connect to PostgreSQL
psql -U postgres

# Run the setup script
\i setup_postgresql.sql
```

2. **Or manually create database and user:**
```sql
-- Create database
CREATE DATABASE synccontents_db;

-- Create user
CREATE USER synccontents_user WITH PASSWORD 'your_strong_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE synccontents_db TO synccontents_user;
```

## 3. Environment Configuration

1. **Copy the example environment file:**
```bash
cp .env.example .env
```

2. **Update the .env file with your PostgreSQL credentials:**
```env
DATABASE_URL=postgresql://synccontents_user:your_password@localhost:5432/synccontents_db
```

## 4. Django Setup

1. **Install/verify PostgreSQL adapter:**
```bash
pip install psycopg2-binary
```

2. **Run Django migrations:**
```bash
# Activate virtual environment
source venv/bin/activate

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## 5. Test the Connection

```bash
# Test database connection
python manage.py dbshell

# Run Django server
python manage.py runserver
```

## 6. Production Considerations

### For production environments:

1. **Use environment variables:**
```env
DATABASE_URL=postgresql://user:password@host:port/dbname
```

2. **Connection pooling** (add to requirements.txt):
```
django-db-connection-pool
```

3. **Backup configuration:**
```bash
# Create backup
pg_dump synccontents_db > backup.sql

# Restore backup
psql synccontents_db < backup.sql
```

### Security Best Practices:

1. **Use strong passwords**
2. **Limit database user privileges**
3. **Configure SSL connections for production**
4. **Regular database backups**
5. **Monitor database performance**

## 7. Common Issues and Solutions

### Connection Issues:
- Check if PostgreSQL service is running
- Verify host, port, username, and password
- Check firewall settings

### Permission Issues:
- Ensure database user has proper privileges
- Check schema ownership

### Migration Issues:
- Drop and recreate database if needed
- Check for conflicting migrations

## 8. Useful Commands

```bash
# Connect to database
psql -U synccontents_user -d synccontents_db

# List databases
\l

# List tables
\dt

# Describe table
\d table_name

# Exit psql
\q
```