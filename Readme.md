# Task Manager - Django Assignment

## Setup Instructions

This project uses `uv` for dependency management and Docker Compose for the MySQL database.

1. **Start the database:**
   Run this in the root directory to spin up MySQL on port 3307:
   `docker compose up -d`

2. **Setup Python environment & Dependencies:**
   `cd backend`
   `uv sync` (or `uv pip install -r requirements.txt` if exporting)
   _(Note: The environment variables are set up in `backend/.env` for local grading convenience)_

3. **Run Migrations & Create User:**
   `uv run python manage.py migrate`
   `uv run python manage.py createsuperuser`

4. **Run the server:**
   `uv run python manage.py runserver`
   Go to `http://127.0.0.1:8000/`

---

## ORM & Database Write-Up

### 1. Overdue Tasks Query

**ORM Call:**
`Task.objects.filter(due_date__lt=today).exclude(status='DONE')`
(Implemented as a custom Model Manager `Task.objects.overdue()`)

**Generated SQL:**
**Reasoning:** Placing this in a custom Manager ensures the logic is reusable across any view or Celery task without repeating the date logic. The `exclude` generates an efficient `NOT` condition in SQL.

### 2. Per-Project Status Counts

**ORM Call:**
**Generated SQL:**
**Reasoning:** Filtering inside the `Count` aggregate uses SQL `CASE WHEN` statements, allowing us to get counts for all three statuses in a single database hit per project, avoiding fetching all tasks into Python memory.

### 3. N+1 Avoidance

**ORM Call Examples:**

- `Task.objects.select_related('project')` (in Dashboard)
- `task.comments.select_related('author').all()` (in Task Detail)

**Reasoning:** In the dashboard, rendering `task.project.name` inside a loop would normally trigger a new query for every single task. `select_related('project')` forces a `SQL INNER JOIN`, retrieving all tasks and their associated project rows in exactly 1 query.

### 4. Database Indexing

**Index Chosen:** Composite index on `(status, due_date)` in the `Task` model.
**Reasoning:** The application explicitly frequently queries for "Overdue" tasks (where `due_date < today` AND `status != 'DONE'`). A composite index perfectly covers this `WHERE` clause, allowing the database engine to quickly seek the exact rows without performing a full table scan on the `tracker_task` table.
